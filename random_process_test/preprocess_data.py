#!/usr/bin/python2.7

import os
import os.path


import sys
import multiprocessing


INFO_MSG = "\nUsage: {0} -dir_path path_value [-perc int_value]\n"


# the below frame is used by worker processes to
# store read data into a temp file.
TEXT_TITLE_FRAME = "temp_stage_{0}_prc_{1}.txt"




def _handle_originals(files, stage, prc_id, percent):
    pass


def _handle_temps(files, stage, prc_id):
    pass




def _process_data(path_to_dir, percent=100):

    # check percentage first
    if percent < 0 or percent > 100:
        raise ValueError("\nPercentage value must be within [0, 100]\n")


    # get references to the files that have to be processed
    # These references will be used later by processes.
    data_files = [d_file for d_file in os.listdir(path_to_dir) if os.path.isfile(os.path.join(path_to_dir, d_file))]


    total_files = len(data_files) # get the number of files
    CPU_COUNT = multiprocessing.cpu_count() # get the number of CPUs


    if total_files == 0 or CPU_COUNT == 0: # nothing to process
        return


    #print "---- Some file size: {0} bytes ----".format(os.path.getsize(os.path.join(path_to_dir, data_files[0])))



    # Step 1: Create a Pool of Python processes
    prc_pool = multiprocessing.Pool(
        processes=CPU_COUNT)


    # Step 2: Handle original text files since the first line
    # should not be written into temp files. Also, percentage
    # is applied to the original files.

    # subdivide tasks into smaller subtasks
    files_per_prc = total_files / CPU_COUNT


    results = [None]*CPU_COUNT # stores results


    # use available processes to subdivide the original files
    global_index = 0

    for prc_idx in xrange(0, CPU_COUNT - 1, 1):
        results[prc_idx] = prc_pool.apply_async(
                _handle_originals,
                (data_files[global_index:global_index+files_per_prc:1],
                1, prc_idx, percent))

        global_index += files_per_prc


    # last process handles the rest
    results[CPU_COUNT - 1] = prc_pool.apply_async(_handle_originals,
            (data_files[global_index::1], 1, CPU_COUNT-1, percent))


    # original files completed
    # now only merging left




    prc_pool.close() # close any incoming tasks
    prc_pool.join()  # wait when the pool terminates


def _process_input(inputs):

    '''
    Check input and return valid values if the input correct


    Possible combinations of input:
        1. -dir_path path_value  [-perc value]
        2. -perc value  -dir_path path_value

        []   -- means optional parameter

        Parameter key and its value must be separated by
        a number of spaces.
    '''

    num_params = len(inputs[1::1]) # passed parameters

    if inputs[1] == "-dir_path" and num_params > 1: # first case

            if num_params == 2:
                return (inputs[2], 100) # default value


            # below cases handle percent part
            dir_value = inputs[2]

            if num_params > 2 and num_params != 4: # exactly two more
                                                   # parameters
                                                   # must be passed
                raise ValueError(INFO_MSG.format(inputs[0]))


            else:
                if inputs[3] == "-perc":
                    try:
                        percent = int(inputs[4], 10)

                        return (dir_value, percent)

                    except ValueError:
                        raise ValueError(INFO_MSG.format(inputs[0]))

                else:
                    raise ValueError(INFO_MSG.format(inputs[0]))


    elif inputs[1] == "-perc" and num_params == 4: # second
                                                   # case

        if inputs[3] == "-dir_path":
            try:
                percent = int(inputs[2], 10)

                return (inputs[4], percent)

            except ValueError:
                pass

        raise ValueError(INFO_MSG.format(inputs[0]))




    else:
        raise ValueError(INFO_MSG.format(inputs[0]))


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print INFO_MSG.format(sys.argv[0])

    else:
        # check inputs
        try:
            path_name, percentage = _process_input(sys.argv)

            # start processing files in the directory
            _process_data(path_to_dir=path_name, percent=percentage)

        except ValueError as exp: # wrong input
            print exp

