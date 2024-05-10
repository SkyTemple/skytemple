"""
This script generates 2 lists of NSIS commands (install&uninstall)
for all files in a given directory

Usage:
    gen_list_files_for_nsis.py  <dir src> <inst list> <uninst list>
Where
    <dir src>       :   dir with sources; must exist
    <inst list>     :   list of files to install (NSIS syntax)
    <uninst list>   :   list of files to uninstall (NSIS syntax)
                        (both these will be overwriten each time)

SOURCE: https://nsis.sourceforge.io/Talk:Uninstall_only_installed_files
"""

import sys
import os

# templates for the output
inst_dir_tpl = '  SetOutPath "$INSTDIR%s"'
inst_file_tpl = '  File "${FILES_SOURCE_PATH}%s"'
uninst_file_tpl = '  Delete "$INSTDIR%s"'
uninst_dir_tpl = '  RMDir "$INSTDIR%s"'

# check args
if len(sys.argv) != 4:
    print(__doc__)
    sys.exit(1)
source_dir = sys.argv[1]
if not os.path.isdir(source_dir):
    print(__doc__)
    sys.exit(1)


def open_file_for_writting(filename):
    """return a handle to the file to write to"""
    try:
        h = open(filename, "w")
    except:
        print("Problem opening file %s for writting" % filename)
        print(__doc__)
        sys.exit(1)
    return h


inst_list = sys.argv[2]
uninst_list = sys.argv[3]
ih = open_file_for_writting(inst_list)
uh = open_file_for_writting(uninst_list)

stack_of_visited = []
counter_files = 0
counter_dirs = 0
print("Generating the install & uninstall list of files")
print("  for directory", source_dir)
print("  ; Files to install\n", file=ih)
print("  ; Files and dirs to remove\n", file=uh)


for cur_dir, dirs, my_files in os.walk(source_dir):
    counter_dirs += 1

    # and truncate dir name
    my_dir = cur_dir[len(source_dir) :]
    my_dir_file = my_dir
    if my_dir == "":
        my_dir = "\\."

    # save it for uninstall
    stack_of_visited.append((my_files, my_dir))

    # build install list
    if len(my_files):
        print(inst_dir_tpl % my_dir, file=ih)
        for f in my_files:
            print(inst_file_tpl % (my_dir_file + os.sep + f), file=ih)
            counter_files += 1
        print("  ", file=ih)

ih.close()
print("Install list done")
print("  ", counter_files, "files in", counter_dirs, "dirs")

stack_of_visited.reverse()
# Now build the uninstall list
for my_files, my_dir in stack_of_visited:
    for f in my_files:
        print(uninst_file_tpl % (my_dir + os.sep + f), file=uh)
    print(uninst_dir_tpl % my_dir, file=uh)
    print("  ", file=uh)

# now close everything
uh.close()
print("Uninstall list done. Got to end.\n")
