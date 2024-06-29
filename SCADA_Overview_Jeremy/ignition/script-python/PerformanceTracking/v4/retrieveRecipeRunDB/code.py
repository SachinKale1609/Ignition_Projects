#import system
#
#def retrieveRecipeRunDataFromDB(machineUniqueName, start, end):
#    """
#    Retrieves recipe run data based on the machine name and specified time range.
#
#    Args:
#        machineUniqueName (str): The unique name combining the system and machine names.
#        start (str): The start time for the query.
#        end (str): The end time for the query.
#        
#    Returns:
#        dataset: The result set from the named query as a dataset.
#    """
#    # Parameters to pass to the named query
#    params = {
#        'MachineName': machineUniqueName,
#        'StartTime': start,
#        'EndTime': end
#    }
#    
#    # Executing the named query and returning the results
#    result = system.db.runNamedQuery("SCADA_Overview/RetrieveRecipeRunData", params)
#    return result
#
#def main(rootTagPath, machineName, start, end):
#    """
#    Main function to process the inputs and retrieve data from the database.
#    
#    Args:
#        rootTagPath (str): The root tag path from which to extract the system name.
#        machineName (str): The name of the machine.
#        start (str): The start time for the query.
#        end (str): The end time for the query.
#    
#    Returns:
#        dataset: The result set from the named query as a dataset.
#    """
#    # Combine root tag path and machine name
#    machineUniqueName = rootTagPath
#    
#    # Remove [SCADA Overview]Performance Tracking/ from the beginning
#    machineUniqueName = machineUniqueName.split("Performance Tracking/", 1)[-1]
#    
#    # Remove the trailing slash
#    machineUniqueName = machineUniqueName.rstrip("/")
#    
#    print('')
#    print(machineUniqueName)
#    print('Querying DB for Runs for ' + machineUniqueName + ' during ' + str(start) + ' to ' + str(end))
#    
#    recipeRunsFromDB = retrieveRecipeRunDataFromDB(machineUniqueName, start, end)
#    
#    Utility.printAsTable(recipeRunsFromDB)
#    return recipeRunsFromDB


import system

def retrieveRecipeRunDataFromDB(machineUniqueName, start, end):
    """
    Retrieves recipe run data based on the machine name and specified time range.

    Args:
        machineUniqueName (str): The unique name combining the system and machine names.
        start (str): The start time for the query.
        end (str): The end time for the query.
        
    Returns:
        dataset: The result set from the named query as a dataset.
    """
    params = {
        'MachineName': machineUniqueName,
        'StartTime': start,
        'EndTime': end
    }
    return system.db.runNamedQuery("SCADA_Overview/RetrieveRecipeRunData", params)

def getMaxEndTime(dataset):
    """
    Finds the maximum 'End Time' value in a dataset.
    
    Args:
        dataset (dataset): The dataset from which to find the maximum 'End Time'.
        
    Returns:
        str: The maximum 'End Time' as a string.
    """
    maxEndTime = None
    for row in range(dataset.getRowCount()):
        endTime = dataset.getValueAt(row, "End Time")
        if maxEndTime is None or endTime > maxEndTime:
            maxEndTime = endTime
    return maxEndTime

def main(rootTagPath, machineName, start, end):
	machineUniqueName = rootTagPath.replace("[SCADA Overview]Performance Tracking/", "").rstrip("/")
	print('Querying DB for Runs for ' + machineUniqueName + ' during ' + str(start) + ' to ' + str(end))
	recipeRunsFromDB = retrieveRecipeRunDataFromDB(machineUniqueName, start, end)
	maxEndTime = getMaxEndTime(recipeRunsFromDB)
	print "\nRetreived info from database
	Utility.printAsTable(recipeRunsFromDB)
	
	print("\nMaximum End Time:", maxEndTime)
	print ''
	print'\n>>>>>>>>> Retreival complete'
	return recipeRunsFromDB


# Example call to the main function
# main('rootTagPath', 'machineName', '2024-05-15 08:00:00 CDT', '202