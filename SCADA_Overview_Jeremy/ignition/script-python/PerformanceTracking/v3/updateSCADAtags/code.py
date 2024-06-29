from com.inductiveautomation.ignition.common import BasicDataset
from java.lang import String, Double
import system
from java.util import Calendar, Date
from java.text import SimpleDateFormat
from math import floor
from system.dataset import toDataSet, addRow, toPyDataSet
import json


def findChildMachines(systemName):
    """
    This function browses the tag structure under a given system name and 
    returns a list of child machine paths excluding any system tags.
    
    :param systemName: The name of the system to browse for child machines.
    :return: A list of child machine paths.
    """
    try:
        # Concatenate the provided system name with the root path.
        rootPath = "[SCADA Overview]Performance Tracking/" + systemName
    
        # Browse the tag structure at the rootPath.
        results = system.tag.browse(rootPath)
    
        # Initialize an empty list to store the paths of child machines.
        paths = []
    
        # Iterate over the results of the browse operation.
        for result in results.getResults():
            # Convert the full path of the current tag to a string.
            fullPathStr = str(result['fullPath'])
    
            # Remove the rootPath part from the fullPathStr to get the relative path.
            # Note: 'browsePath' should be 'rootPath' based on the context.
            filteredFullPath = fullPathStr.replace(rootPath, "")
    
            # If the filtered path starts with '/', remove this leading slash.
            if filteredFullPath.startswith('/'):
                filteredFullPath = filteredFullPath[1:]
    
            # Add the path to the list only if it's not the '_ System' tag.
            if filteredFullPath != '_ System':
                paths.append(filteredFullPath)
    
        # Return the list of found child machine paths.
        return paths
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in findChildMachines: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.findChildMachines', 'Error2': 'Error finding child machines', 'Error3': str(e)})

def countOn(tagPath, queryStart, queryEnd):
    """
    Performs a CountOn query for a specified tag over a shift.

    :param tagPath: Path of the tag
    :param queryStart: Start time of query
    :param queryEnd: End time of query
    :return: Result of the CountOn query
    """
    try:
        start = queryStart
        end = queryEnd
        paths = [tagPath]
        countResult = system.tag.queryTagCalculations(paths, ["CountOn"], start, end)
        return int(countResult.getValueAt(0, 1))
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in countOn: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.countOn', 'Error2': 'Error performing CountOn query', 'Error3': str(e)})

def durationOn(tagPath, queryStart, queryEnd):
    """
    Performs a DurationOn query for a specified tag over a shift.

    :param tagPath: Path of the tag
    :param queryStart: Start time of query
    :return: Result of the DurationOn query or 0 if None
    """
    try:
        start = queryStart
        end = queryEnd
        paths = [tagPath]
        durationResult = system.tag.queryTagCalculations(paths, ["DurationOn"], start, end)
        return durationResult.getValueAt(0, 1) if durationResult is not None else 0
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in durationOn: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.durationOn', 'Error2': 'Error performing DurationOn query', 'Error3': str(e)})


def createTagPaths(rootTagPath, machineName):
    """
    Constructs and returns the tag paths for various machine statuses and operational data.

    :param rootTagPath: The root path for tag paths.
    :param machineName: The name of the machine within the system.
    :return: Dictionary of tag paths.
    """
    try:
        tagPaths = {
            'cycleDone': rootTagPath + 'machineStatus/Cycle Done',
            'inCycle': rootTagPath + 'machineStatus/In Cycle',
            'idle': rootTagPath + 'machineStatus/Machine Idle',
            'activeRecipe': rootTagPath + 'Active Recipe',
            'shiftRunTime': rootTagPath + 'Shift Run Time',
            'shiftIdleTime': rootTagPath + 'Shift Idle Time',
            'shiftDownTime': rootTagPath + 'Shift Down Time',
            'partsComplete': rootTagPath + 'Parts Complete',
            'expectedParts': rootTagPath + 'Expected Parts'
        }
    
        return tagPaths
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in createTagPaths: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.createTagPaths', 'Error2': 'Error creating tag paths', 'Error3': str(e)})

def writeToTags(tagPathDict, dataDict):
    """
    Writes aggregated data to the system tags.

    :param tagPathDict: Dictionary of tag paths.
    :param dataDict: Dictionary containing the data to be written to each tag.
    """
    try: 
        for tag, value in dataDict.items():
            tagPath = tagPathDict.get(tag)
            if tagPath:
                system.tag.write(tagPath, value)
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in writeToTags: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.writeToTags', 'Error2': 'Error writing data to tags', 'Error3': str(e)})

def getActiveRecipes(tagPath, machineName, activeRecipes):
    """
    Retrieves and processes recipe information for a given machine and appends to the active recipes list.

    :param tagPath: The tag path for the active recipe.
    :param machineName: The name of the machine.
    :param activeRecipes: List to append the active recipe data.
    """
    try:
        activeRecipe = system.tag.read(tagPath).value
        queryPath = "scadaGetRecipe"
        queryParams = {"machineName": machineName, "recipeName": activeRecipe}
    
        result = system.db.runNamedQuery(queryPath, queryParams)
        for row in result:
            rowDict = {
                "MachineName": machineName,
                "RecipeName": row["RecipeName"],
                "SetupTime": row["SetupTime"],
                "CycleTarget": row["CycleTarget"]
            }
            activeRecipes.append(rowDict)
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getActiveRecipes: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getActiveRecipes', 'Error2': 'Error retrieving active recipes', 'Error3': str(e)})

def main(systemNames, shiftStartHours):
    """
    Queries tag history for multiple systems and performs data aggregation on Historical Tag Paths.

    Args:
        systemNames: A list of system names to query.
        shiftStartHours: List of hours at which the shift starts.
    """
    try:
        for systemName in systemNames:
            # Find all child machines for a given system name, excluding system tags
            machineNames = findChildMachines(systemName)            

            # Define the end time for the query as the current time
            end = system.date.now()
            # Calculate the start time of the current shift
            shiftStartTime = Utility.getCurrentShiftStart(shiftStartHours)

            for machineName in machineNames:
                # Construct the root tag path for each machine
                rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
                # Create tag paths for various machine statuses and operational data
                tagPaths = createTagPaths(rootTagPath, machineName)

                # Set the start and end time for the data query
                queryStart = shiftStartTime
                queryEnd = end

                # Get recipe run information for the machine within the shift period
                recipeRunData = PerformanceTracking.v3.getRecipeRunInfo.main(systemName, machineName, queryStart, queryEnd)

                # Calculate the total expected parts from the recipe run data
                expectedPartsIndex = recipeRunData.getColumnIndex("Expected Parts")
                totalExpectedParts = sum(recipeRunData.getValueAt(row, expectedPartsIndex) for row in range(recipeRunData.getRowCount()))

                # Count completed parts within the shift
                partsComplete = countOn(tagPaths['cycleDone'], queryStart, queryEnd)
                # Calculate idle time in minutes for the shift
                shiftIdleTime = round(durationOn(tagPaths['idle'], queryStart, queryEnd) / 60.0, 2)
                # Calculate run time in minutes for the shift
                shiftRunTime = round(durationOn(tagPaths['inCycle'], queryStart, queryEnd) / 60.0, 2)
                # Calculate total time in minutes from shift start to current time
                timeDifferenceInMinutes = round((end.getTime() - shiftStartTime.getTime()) / 60000.0, 2)
                # Determine downtime by subtracting idle and run time from total time
                shiftDownTime = timeDifferenceInMinutes - shiftIdleTime - shiftRunTime
                # Aggregate data to be written to system tags
                dataToWrite = {
                    'shiftRunTime': shiftRunTime,
                    'shiftIdleTime': shiftIdleTime,
                    'shiftDownTime': shiftDownTime,
                    'expectedParts': totalExpectedParts,
                    'partsComplete': partsComplete
                }
                # Write aggregated data to the system tags
                writeToTags(tagPaths, dataToWrite)

                # Retrieve and process active recipe information
                activeRecipes = []
                getActiveRecipes(tagPaths['activeRecipe'], machineName, activeRecipes)
            
            #PerformanceTracking.v3.updateSystemScore.main(startTime, endTime, systemName)
                
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in main: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.main', 'Error2': 'Error in main function', 'Error3': str(e)})
        
        
def diagnostic(systemNames, shiftStartHours):
    """
    Queries tag history for multiple systems and performs data aggregation on Historical Tag Paths.

    Args:
        systemNames: A list of system names to query.
        shiftStartHours: List of hours at which the shift starts.
    """
    for systemName in systemNames:
        print("\nProcessing system: {}".format(systemName))

        # Find all child machines for a given system name, excluding system tags
        machineNames = findChildMachines(systemName)            
        print("Found child machines: {}".format(machineNames))

        # Define the end time for the query as the current time
        end = system.date.now()
        print("End time for the query: {}".format(end))

        # Calculate the start time of the current shift
        shiftStartTime = Utility.getCurrentShiftStart(shiftStartHours)
        print("Shift start time: {}".format(shiftStartTime))

        for machineName in machineNames:
            print("\nProcessing machine: {}".format(machineName))

            # Construct the root tag path for each machine
            rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
            # Create tag paths for various machine statuses and operational data
            tagPaths = createTagPaths(rootTagPath, machineName)
            print("Root tag path: {}".format(rootTagPath))

            # Create tag paths for various machine statuses and operational data
            print("Tag paths: {}".format(tagPaths))

            # Set the start and end time for the data query
            queryStart = shiftStartTime
            queryEnd = end

            print("Query start time: {}".format(queryStart))
            print("Query end time: {}".format(queryEnd))


            # Get recipe run information for the machine within the shift period
            recipeRunData = PerformanceTracking.v3.getRecipeRunInfo.main(systemName, machineName, queryStart, queryEnd)
            print("Recipe run data retrieved")
            Utility.printAsTable(recipeRunData)

            # Calculate the total expected parts from the recipe run data
            expectedPartsIndex = recipeRunData.getColumnIndex("Expected Parts")
            totalExpectedParts = sum(recipeRunData.getValueAt(row, expectedPartsIndex) for row in range(recipeRunData.getRowCount()))
            print("Total expected parts: {}".format(totalExpectedParts))

            # Count completed parts within the shift
            partsComplete = countOn(tagPaths['cycleDone'], queryStart, queryEnd)
            print("Parts completed: {}".format(partsComplete))
            
            # Count completed cycles within the shift
            partsComplete = countOn(tagPaths['inCycle'], queryStart, queryEnd)
            print("Cycles completed: {}".format(partsComplete))

            # Calculate idle time in minutes for the shift
            shiftIdleTime = round(durationOn(tagPaths['idle'], queryStart, queryEnd) / 60.0, 2)
            print("Shift idle time (minutes): {}".format(shiftIdleTime))

            # Calculate run time in minutes for the shift
            shiftRunTime = round(durationOn(tagPaths['inCycle'], queryStart, queryEnd) / 60.0, 2)
            print("Shift run time (minutes): {}".format(shiftRunTime))

            # Calculate total time in minutes from shift start to current time
            timeDifferenceInMinutes = round((end.getTime() - shiftStartTime.getTime()) / 60000.0, 2)
            print("Time difference in minutes: {}".format(timeDifferenceInMinutes))

            # Determine downtime by subtracting idle and run time from total time
            shiftDownTime = timeDifferenceInMinutes - shiftIdleTime - shiftRunTime
            print("Shift downtime (minutes): {}".format(shiftDownTime))

            # Retrieve and process active recipe information
            activeRecipes = []
            getActiveRecipes(tagPaths['activeRecipe'], machineName, activeRecipes)
            print("Active recipes: {}".format(activeRecipes))