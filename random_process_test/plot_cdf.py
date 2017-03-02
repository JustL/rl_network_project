#!/usr/bin/python2.7

import numpy
import pandas
import matplotlib.pyplot as pylt
import os.path
import sys
import multiprocessing



USAGE_MSG  = "\nUsage: {0} file(s)_to_plot [-x_label 'l_x'] [-y_label 'l_y'] [-title 'title'] [-save_file file]\n\nfile(s)_to_plot -- file(s) whose CDF(s) to plot on one graph;\n\n'l_x' (optional) -- x label title (surrounded by single/double  quotation marks);\n\n'l_y' (optional) -- y label title (surrounded by single/double quotation marks);\n\n'title' (optional) -- title that will be added to the graph (surrounded by single/double quotation marks);\n\nfile (optional) -- if the user wants to save the plot instead of displaying it, pass a file."





AVAIL_COLORS = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow',
        'black']





def _compute_cdf_data(file_name, file_data):


    # only need FCTs (second column)
    fct_name = file_data.columns.values[1]
    sorted_fcts = numpy.sort(file_data[fct_name]) # FCTs sorted in
                                                  # ascending order

    cdf_arr = numpy.array(xrange(
        sorted_fcts.shape[0])) / float(sorted_fcts.shape[0])


    # get proper name for this data set
    dir_part, file_part = os.path.split(file_name)

    file_part = file_part.split(".")[0] # discard file extension

    return (sorted_fcts, cdf_arr, file_part)




'''
This function is used by created python processes for reading
data from the pased files and computing their cdfs.

   Args:
       res_queue : queue that stores all computed cdfs for
                   later plotting
       d_files   : files to read and whose cdfs have to be computed

'''
def _read_and_compute_cdf(res_queue, d_files):


    if not d_files: # if there are not files to read
        return

    for d_name in d_files:
        # read a file
        try:
            read_data = pandas.read_csv(d_name)

            # compute CDFs structures
            cdf_item = _compute_cdf_data(d_name, read_data)


            # a file has been read, its CDF has been computed
            res_queue.put(cdf_item, block=True)  # it is ensured
                                                 # that the queue
                                                 # is big enough for
                                                 # all files


        except: # ignore all exceptions
            pass



'''
This is a core function since it does all the plotting.
The function receives a list of numpy arrays and plots their
content on the computer screen.

    Args:
        cdf_arrays   :   list of tuples that store numpy arrays for CDFs
        x_label      :   label for plotting
        y_label      :   label for plotting
        graph_title  :   title that will be displayed on the graph
        save_file    :   file where the plot is saved
'''
def _perform_plot(cdf_arrays, x_label, y_label,
        graph_title, save_file=None):


    if not cdf_arrays: # if no data to plot
        return


    # set all labels first
    x_axis_properties = {
            'fontsize'            :      '12',
            'verticalalignment'   :      'top',
            'horizontalalignment' :      'center'
            }

    y_axis_properties = {
            'fontsize'            :       '12',
            'verticalalignment'   :       'center',
            'horizontalalignment' :       'right',
            'rotation'            :       'vertical'
            }

    title_properties = {
            'fontsize'            :       '16',
            'verticalalignment'   :       'top',
            'horizontalalignment' :       'center'
            }


    pylt.xlabel(x_label, **x_axis_properties)
    pylt.ylabel(y_label, **y_axis_properties)
    pylt.suptitle(graph_title, **title_properties)


    # iterate though all files and display each of them
    # on the graph

    col_index = 0 # color index for plotting

    # for scaling the x and y axes
    EXTRA_SPACE_X = 1000000 # look at code below to know the meaning
    axis_y_min = 0.0
    axis_y_max = 1.2
    axis_x_min = 0.0
    axis_x_max = -1.0 # only this value has to be found

    for data_plot in cdf_arrays:

        pylt.plot(data_plot[0], data_plot[1],
            color = AVAIL_COLORS[col_index],
            label = '{}'.format(data_plot[2])
        )

        col_index += 1 # change the color
        # find maximum completion time
        if data_plot[0][-1] > axis_x_max:
            # FCTs have been sorted in
            # ascending order
            axis_x_max = data_plot[0][-1]


    # give some extra space for axis_x_max to make
    # the figure nicer
    axis_x_max += EXTRA_SPACE_X

    # add a legend and show or save the resulting figure
    pylt.legend(loc="upper right")
    pylt.axis([axis_x_min, axis_x_max, axis_y_min, axis_y_max])

    if save_file != None: # means needs to be saved
        pylt.savefig(save_file, bbox_inches="tight")

    else:                 # means display the graph
        pylt.show()




def _plot_CDF(data_files, graph_options):

    if len(data_files) > len(AVAIL_COLORS):
        raise ValueError("There are no enough colors to plot all CDFs\n")


    # graph plotting parameters
    x_label = graph_options["-x_label"]
    y_label = graph_options["-y_label"]
    graph_title = graph_options["-title"]
    plot_file = graph_options["-save_file"]

    comp_cdfs = []  # stores tuples of numpy arrays for plotting


    if len(data_files) > 1:

        NUM_OF_FILES = len(data_files)
        CPU_COUNT = multiprocessing.cpu_count()

        if CPU_COUNT < 1:
            raise RuntimeError("CPU count is less than 1\n")

        cdf_queue = multiprocessing.Queue(maxsize=NUM_OF_FILES)
        prc_pool = [] # pool of processes



        if CPU_COUNT > NUM_OF_FILES:
            # each file is preprocessed by a different
            # process

            for d_file in data_files:
                # create a new process and
                # pass arguments to it
                temp_list = [d_file]
                temp_prc = multiprocessing.Process(
                    target=_read_and_compute_cdf,
                    args=(cdf_queue, temp_list))

                prc_pool.append(temp_prc)
                temp_prc.start() # start a new process


        else: # distribute among the CPUs equally

            jobs_per_cpu = NUM_OF_FILES / CPU_COUNT

            global_index  = 0 # for keeping track of the number
                              # of jobs already scheduled

            for _ in xrange(0, CPU_COUNT - 1, 1):

                # create a new process and pass
                # appropriate arguments to it
                temp_prc = multiprocessing.Process(
                    target=_read_and_compute_cdf,
                    args=(cdf_queue,
                    data_files[global_index:global_index+jobs_per_cpu:1]))

                prc_pool.append(temp_prc)
                # start the newly created process
                temp_prc.start()

                global_index += jobs_per_cpu # update global index


            # for the last process give the rest of files
            last_prc = multiprocessing.Process(
                target=_read_and_compute_cdf,
                args=(cdf_queue, data_files[global_index::1]))

            prc_pool.append(last_prc)
            last_prc.start()


        # fisrt read all files from the queue before joining
        # since Queue uses a buffer and a process cannot termiante
        # until the buffer is flushed. As a result, reading first
        # is crucial.
        read_cdfs = 0

        while read_cdfs < NUM_OF_FILES:
            # wait for another process to
            # enqueue a CDF structure
            comp_cdfs.append(cdf_queue.get(block=True))
            read_cdfs += 1

        # wait for all processes to finish before plotting
        for prc_stop in prc_pool:
            prc_stop.join()         # wait until a process finishes



    else: # just do simple computing

        for d_file in data_files:
            try:
                read_data = pandas.read_csv(d_file)


                # add a CDF to the list that is plotted
                comp_cdfs.append(_compute_cdf_data(
                    d_file, read_data))

            except: # ignore all exceptions
                pass



    # for both cases use the same interface
    _perform_plot(comp_cdfs, x_label, y_label,
            graph_title, save_file=plot_file)





'''
Helper function to check if the figre_file
refers to an existing directory.

  return : if no such path exists : True
'''
def _no_path(figure_file):

    # need to handle two cases

      # Case 1: the file in the same directory;
      # Case 2: the file in a different directory.

    dir_part, file_part = os.path.split(figure_file)

    if file_part != "" and dir_part == "":   # same directory
        return False

    elif file_part == "" and dir_part != "": # no filename
        return True

    elif file_part != "" and dir_part != "": # filename passed
        return not os.path.isdir(dir_part)   # check if dir exists


    return True




'''
Helper function for checking passed optioons to the script
'''
def _preprocess_input(inputs):


    # return values
    cdf_files = []
    plot_options = {"-x_label" : "Time (us)", "-y_label" : "CDF", "-title" : "FCTs", "-save_file" : None}


    # read inputs and map them to the correct values
    input_length = len(inputs)
    loc_index = 1

    while loc_index < input_length:

        # if the value is one of the parameters
        # check if it is in the appropriate place
        if inputs[loc_index] in plot_options:
            if not cdf_files or (loc_index + 1) == input_length:
                raise ValueError(USAGE_MSG.format(inputs[0]))
            else: # set appropriate parameters
                plot_options[inputs[loc_index]] = inputs[loc_index+1]
                loc_index += 2

        else: # just append a new file if it exists
            if not os.path.isfile(inputs[loc_index]):
                raise ValueError(USAGE_MSG.format(inputs[0]))

            cdf_files.append(inputs[loc_index])
            loc_index += 1


    # check if the passed path exists:
    if plot_options["-save_file"] != None and _no_path(plot_options["-save_file"]):
        raise RuntimeError("Your passed path to a file does not exist!\n")


    return (cdf_files, plot_options)





if __name__ == "__main__":

    if len(sys.argv) < 2:
        print USAGE_MSG.format(sys.argv[0])

    else:
        try:
            input_files, pre_labels = _preprocess_input(sys.argv)
            _plot_CDF(input_files, pre_labels)
        except ValueError:
            raise

        except RuntimeError:
            raise



