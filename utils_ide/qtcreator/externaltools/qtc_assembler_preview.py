#!/usr/bin/env python3

"""
Takes 2 args

 qtc_assembler_preview.py <build_dir> <file.c/c++>

Currently GCC is assumed
"""


import sys
import os
import shlex
import subprocess

BUILD_DIR = sys.argv[-2]
SOURCE_FILE = sys.argv[-1]

# TODO, support other compilers
COMPILER_ID = 'GCC'

def find_arg(source, data):
    source_base = os.path.basename(source)
    for l in data:
        # chances are high that we found the file
        if source_base in l:
            # check if this file is in the line
            l_split = shlex.split(l)
            for w in l_split:
                if w.endswith(source_base):
                    if os.path.isabs(w):
                        if os.path.samefile(w, source):
                            # print(l)
                            return l
                    else:
                        # check trailing path (a/b/c/d/e.c == d/e.c)
                        w_sep = os.path.normpath(w).split(os.sep)
                        s_sep = os.path.normpath(source).split(os.sep)
                        m = min(len(w_sep), len(s_sep))
                        if w_sep[-m:] == s_sep[-m:]:
                            # print(l)
                            return l


def find_build_args_ninja(source):
    make_exe = "ninja"
    process = subprocess.Popen([make_exe, "-t", "commands"],
                                stdout=subprocess.PIPE,
                               )
    while process.poll():
        time.sleep(1)

    out = process.stdout.read()
    process.stdout.close()
    # print("done!", len(out), "bytes")
    data = out.decode("utf-8", errors="ignore").split("\n")
    return find_arg(source, data)

def find_build_args_make(source):
    make_exe = "make"
    process = subprocess.Popen([make_exe, "--always-make", "--dry-run", "--keep-going", "VERBOSE=1"],
                                stdout=subprocess.PIPE,
                               )
    while process.poll():
        time.sleep(1)

    out = process.stdout.read()
    process.stdout.close()

    # print("done!", len(out), "bytes")
    data = out.decode("utf-8", errors="ignore").split("\n")
    return find_arg(source, data)

def main():

    # currently only supports ninja or makefiles
    build_file_ninja = os.path.join(BUILD_DIR, "build.ninja")
    build_file_make = os.path.join(BUILD_DIR, "Makefile")
    if os.path.exists(build_file_ninja):
        print("Using Ninja")
        arg = find_build_args_ninja(SOURCE_FILE)
    elif os.path.exists(build_file_make):
        print("Using Make")
        arg = find_build_args_make(SOURCE_FILE)
    else:
        sys.stderr.write("Can't find Ninja or Makefile (%r or %r), aborting" % (build_file_ninja, build_file_make))
        return

    if arg is None:
        sys.stderr.write("Can't find file %r in build command output of %r, aborting" % (SOURCE_FILE, BUILD_DIR))
        return

    # now we need to get arg and modify it to produce assembler
    arg_split = shlex.split(arg)

    # get rid of: 'cd /a/b/c && ' prefix used by make (ninja doesn't need)
    try:
        i = arg_split.index("&&")
    except ValueError:
        i = -1
    if i != -1:
        del arg_split[:i + 1] 

    if COMPILER_ID == 'GCC':
        # remove arg pairs
        for arg, n in (("-o", 2), ("-MF", 2), ("-MT", 2), ("-MMD", 1)):
            if arg in arg_split:
                i = arg_split.index(arg)
                del arg_split[i : i + n]

        # --- Switch debug for optimized ---
        for arg, n in (("-O0", 1),
                       ("-g", 1), ("-g1", 1), ("-g2", 1), ("-g3", 1),
                       ("-ggdb", 1), ("-ggdb", 1), ("-ggdb1", 1), ("-ggdb2", 1), ("-ggdb3", 1),
                       ("-fno-inline", 1),
                       ("-DDEBUG", 1), ("-D_DEBUG", 1),
                       ):
            if arg in arg_split:
                i = arg_split.index(arg)
                del arg_split[i : i + n]

        # add optimized args
        arg_split += ["-O3", "-fomit-frame-pointer", "-DNDEBUG", "-Wno-error"]

        # not essential but interesting to know
        arg_split += ["-ftree-vectorizer-verbose=1"]

        arg_split += ["-S"]
        # arg_split += ["-masm=intel"]  # optional
        # arg_split += ["-fverbose-asm"]  # optional but handy
    else:
        sys.stderr.write("Compiler %r not supported" % COMPILER_ID)
        return

    source_asm = SOURCE_FILE + ".asm"

    # Never overwrite existing files
    i = 1
    while os.path.exists(source_asm):
        source_asm = SOURCE_FILE + ".asm.%d" % i
        i += 1

    arg_split += ["-o", source_asm]

    # print("Executing:", arg_split)
    subprocess.call(arg_split)

    if not os.path.exists(source_asm):
        sys.stderr.write("Did not create %r from calling %r" % (source_asm, " ".join(arg_split)))
        return
    print("Running: %r" % " ".join(arg_split))
    print("Created: %r" % source_asm)


if __name__ == "__main__":
    main()