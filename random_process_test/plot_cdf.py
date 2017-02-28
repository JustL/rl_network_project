#!/usr/bin/python2.7

import numpy
import pandas
import matplotlib.pyplot as pylt
import os.path
import sys
import multiprocessing
import Queue



USAGE_MSG  = "\nUsage: {0} file_to_plot [-x_label 'l_x'] [-y_label 'l_y'] [-title 'title']\n\nfile_to_plot -- file(s) whose CDF(s) to plot on one graph;\n\n'l_x' (optional) -- x label title (surrounded by single/double  quotation marks);\n\n'l_y' (optional) -- y label title (surrounded by single/double quotation marks);\n\n'title' (optional) -- title that will be added to the graph (surrounded by single/double quotation marks)."





AVAIL_COLORS = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow',
        'black']





def _compute_cdf_data(file_name, file_data):


    # only need FCTs (second column)
    fct_name = file_data.columns.values[1]
    sorted_fcts = numpy.sort(file_data[fct_name]) # FCTs sorted in
                                                  # ascending order

    cdf_arr = numpy.array(xrange(
        sorted_fcts.shape[0])) / float(sorted_fcts.shape[0])

    return (sorted_fcts, cdf_arr, file_name)




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
'''
def _perform_plot(cdf_arrays, x_label, y_label, graph_title):


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

    for data_plot in cdf_arrays:

        pylt.plot(data_plot[0], data_plot[1],
            color = AVAIL_COLORS[col_index],
            label = '{}'.format(data_plot[2])
        )

        col_index += 1 # change the color


    # add a legend and show the resulting graph
    pylt.legend(loc="upper right")
    pylt.show()




def _plot_CDF(data_files, graph_labels):

    if len(data_files) > len(AVAIL_COLORS):
        raise ValueError("There are no enough colors to plot all CDFs\n")


    # graph plotting parameters
    x_label = graph_labels["-x_label"]
    y_label = graph_labels["-y_label"]
    graph_title = graph_labels["-title"]
    comp_cdfs = []  # stores tuples of numpy arrays for plotting


    if len(data_files) > 1:

        NUM_OF_FILES = len(data_files)
        CPU_COUNT = multiprocessing.cpu_count()

        if CPU_COUNT < 1:
            raise RuntimeError("CPU count is less than 1\n")

        cdfs = multiprocessing.Queue(maxsize=NUM_OF_FILES)
        prc_pool = [] # pool of processes



        if CPU_COUNT > NUM_OF_FILES:
            # each file is preprocessed by a different
            # process

            for d_file in data_files:
                # create a new process and
                # pass arguments to it
                temp_list = [d_file]
                prc_pool.append(multiprocessing.Process(
                    target=_read_and_compute_cdf,
                    args=(cdfs, temp_list)))

                prc_pool[-1].start() # start a new process


        else: # distribute among the CPUs equally

            jobs_per_cpu = NUM_OF_FILES / CPU_COUNT

            global_index  = 0 # for keeping track of the number
                              # of jobs already scheduled

            for _ in xrange(0, CPU_COUNT - 1, 1):

                # create a new process and pass
                # appropriate arguments to it
                prc_pool.append(multiprocessing.Process(
                    target=_read_and_compute_cdf,
                    args=(cdfs,
                    data_files[global_index:global_index+jobs_per_cpu:1])))

                # start the newly created process
                prc_pool[-1].start()

                global_index += jobs_per_cpu # update global index


            # for the last process give the rest of files
            prc_pool.append(multiprocessing.Process(
                target=_read_and_compute_cdf,
                args=(cdfs, data_files[global_index::1])))

            prc_pool[-1].start()


        # wait for all processes to finish before plotting
        for prc_stop in prc_pool:
            prc_stop.join()         # wait until a process finishes

        # all the started processes have finished
        try:
            # read the computed cdfs into a list
            while 1:
                comp_cdfs.append(cdfs.get(block=False))

        except Queue.Empty:
            # done reading cdfs
            pass


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
    _perform_plot(comp_cdfs, x_label, y_label, graph_title)



def _preprocess_input(inputs):


    # return values
    cdf_files = []
    labels = {"-x_label" : "Time (us)", "-y_label" : "CDF", "-title" : "FCTs"}


    # read inputs and map them to the correct values
    input_length = len(inputs)
    loc_index = 1

    while loc_index < input_length:

        # if the value is one of the parameters
        # check if it is in the appropriate place
        if inputs[loc_index] in labels:
            if not cdf_files or (loc_index + 1) == input_length:
                raise ValueError(USAGE_MSG)
            else: # set appropriate parameters
                labels[inputs[loc_index]] = inputs[loc_index+1]
                loc_index += 2

        else: # just append a new file if it exists
            if not os.path.isfile(inputs[loc_index]):
                raise ValueError(USAGE_MSG)

            cdf_files.append(inputs[loc_index])
            loc_index += 1



    return (cdf_files, labels)





if __name__ == "__main__":

    if len(sys.argv) < 2:
        print USAGE_MSG

    else:
        try:
            input_files, pre_labels = _preprocess_input(sys.argv)
            _plot_CDF(input_files, pre_labels)
        except ValueError:
            raise

        except RuntimeError:
            raise



