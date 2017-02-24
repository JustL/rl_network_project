#!/usr/bin/python2.7

import os
import os.path


import sys
import multiprocessing


INFO_MSG = "\nUsage: {0} -dir_path path_value [-perc int_value]\n\npath_value -- relative or absolute path to the directory that stores files;\n\nint_value -- integer that determines what percentage of the  data in a file is only processed (percentage measured from the end of a file)."


# the below frame is used by worker processes to
# store read data into a temp file.
TEXT_TITLE_FRAME = "temp_stage_{0}_prc_{1}.txt"
FINAL_FILE_TITLE = "processed_data_file.csv"


MAX_PERCENT = 100
MIN_PERCENT = 1


def _handle_originals(dir_path, d_files, stage, prc_id, percent):


    if len(d_files) == 0 or len(d_files) == 1: # nothing to combine
        return

    # there are two cases:
    #    1. percent < 100;
    #    2. percent == 100.

    if percent == MAX_PERCENT: # read full files but
                               # ignore the first line

        # create a new file for combining all other values
        temp_file = os.path.join(dir_path,
                TEXT_TITLE_FRAME.format(stage, prc_id))



        with open(temp_file, "w") as w_file:

            # loop through all passed files
            # and process them
            for r_file in d_files:

                skip_line = True
                with open(os.path.join(dir_path, r_file), "r") as fd:
                    for line in fd:
                        if skip_line: # ignore first line
                            skip_line = False
                            continue

                        # write a line to the w_file
                        w_file.write(line)


    else: # only last few lines should be read


        percent = percent / 100.0
        # create a new file for combining all other values
        temp_file = os.path.join(dir_path,
                TEXT_TITLE_FRAME.format(stage, prc_id))

        with open(temp_file, "w") as w_file:

            # loop through all passed files
            # and process them
            for r_file in d_files:

                file_size = os.path.getsize(os.path.join(dir_path, r_file))
                start_read_from = int(file_size*percent)
                skip_line = True

                with open(os.path.join(dir_path, r_file), "r") as fd:
                    fd.seek(-start_read_from, 2) # go to this offset
                                                 # before the end of
                                                 # the file

                    for line in fd:
                        if skip_line: # ignore first line
                            skip_line = False
                            continue

                        # write a line to the w_file
                        w_file.write(line)



'''
Function handles intermediate files so that merges previous stage
files and deletes them.
'''
def _handle_temps(dir_path, cmb_files, stage, prc_id):

    if cmb_files[0] == cmb_files[1]: # means nothing to combine
        return

    # all stages follow the same title pattern. So, this function
    # has to read files from previous stages passed in cmb_files
    # and after reading them delete them -- save storage.

    temp_file = os.path.join(dir_path,
            TEXT_TITLE_FRAME.format(stage, prc_id))

    beg_range = cmb_files[0] # beginning of the range
    end_range = cmb_files[1] # the end of range file


    with open(temp_file, "w") as w_file:


        for cur_f_range in xrange(beg_range, end_range + 1, 1):
            # just open, read and delete files from
            # previous stage
            read_temp = os.path.join(dir_path,
                TEXT_TITLE_FRAME.format(stage-1, cur_f_range))

            with open(read_temp, "r") as fd:
                # read line by line
                # and append it to the new
                # open file
                for line in fd:
                    w_file.write(line)

            # file has been read and closed
            # now need to delete it
            os.remove(read_temp)



def _process_data(path_to_dir, percent=MAX_PERCENT):

    # check percentage first
    if percent < MIN_PERCENT or percent > MAX_PERCENT:
        raise ValueError("\nPercentage value must be in [{0}, {1}]\n".format(MIN_PERCENT, MAX_PERCENT))

    # check if the path is a directory
    if not os.path.isdir(path_to_dir):
        raise ValueError("\n'{0}' is not a directory\n".format(path_to_dir))

    # get references to the files that have to be processed
    # These references will be used later by processes.
    data_files = [d_file for d_file in os.listdir(path_to_dir) if os.path.isfile(os.path.join(path_to_dir, d_file))]


    total_files = len(data_files) # get the number of files
    CPU_COUNT = multiprocessing.cpu_count() # get the number of CPUs


    if total_files == 0 or CPU_COUNT == 0: # nothing to process
        return


    # two cases to handle
    # Case 1: total_files > CPU_COUNT
    # Case 2: total_files <= CPU_COUNT

    # get the number of processes to create
    PROCESS_NUM = CPU_COUNT # initiailize to CPU count

    # for keeping track of the final temp file
    final_temp_prc_id = 0
    final_temp_stage  = 0

    if total_files <= CPU_COUNT:
        PROCESS_NUM = total_files / 2 if total_files > 3 else 1


    # Step 1: Create a Pool of Python processes
    prc_pool = multiprocessing.Pool(
            processes=PROCESS_NUM)


    # Step 2: Handle original text files since the first line
    # should not be written into temp files. Also, percentage
    # is applied to the original files.

    # subdivide tasks into smaller subtasks
    files_per_prc = total_files / PROCESS_NUM


    results = [None]*PROCESS_NUM # stores results


    # use available processes to subdivide the original files
    global_index = 0

    for prc_idx in xrange(0, PROCESS_NUM - 1, 1):
        results[prc_idx] = prc_pool.apply_async(
            _handle_originals,
            (path_to_dir,
            data_files[global_index:global_index+files_per_prc:1],
                1, prc_idx, percent))

        global_index += files_per_prc


    # last process handles the rest
    results[PROCESS_NUM - 1] = prc_pool.apply_async(_handle_originals,
        (path_to_dir,
        data_files[global_index::1],
        1, PROCESS_NUM-1, percent))


    # update final constant
    final_temp_prc_id = PROCESS_NUM - 1
    final_temp_stage = 1

    # wait for all processes to complete
    for prc_state in results:
        prc_state.wait()      # means all processes have completed


    # original files completed
    # now only merging left
    left_files = PROCESS_NUM # current number of intermediate files
    stage_value = 2          # first stage was finished above


    while left_files != 1: # keep merging until work only for one
                           # process is left

        num_cpus = left_files / 2 # calculate num of cpus to use

        files_per_proc = left_files / num_cpus

        global_index = 0

        # similar to the above code
        for prc_idx in xrange(0, num_cpus - 1, 1):
            results[prc_idx] = prc_pool.apply_async(
                _handle_temps, (path_to_dir,
                (global_index, global_index + files_per_proc - 1),
                stage_value, prc_idx))

            global_index += files_per_proc


        # for the last process, deal with the remaining files
        results[num_cpus-1] = prc_pool.apply_async(
            _handle_temps, (path_to_dir,
            (global_index, left_files - 1),
            stage_value, num_cpus-1))

        # update all constants
        final_temp_prc_id = num_cpus - 1
        final_temp_stage = stage_value

        stage_value += 1 # increment the stage
        left_files = num_cpus # new value of remaining vals

        # now wait until all processes complete
        for wait_idx in xrange(0, num_cpus, 1):
            results[wait_idx].wait()


        # restart the while loop



    # all data files have been merged into
    # one big data file

    prc_pool.close() # close any incoming tasks
    prc_pool.join()  # wait when the pool terminates

    # rename the final file
    os.rename(os.path.join(path_to_dir,
        TEXT_TITLE_FRAME.format(final_temp_stage, final_temp_prc_id)),
        os.path.join(path_to_dir, FINAL_FILE_TITLE))


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
                return (inputs[2], MAX_PERCENT) # default value


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

