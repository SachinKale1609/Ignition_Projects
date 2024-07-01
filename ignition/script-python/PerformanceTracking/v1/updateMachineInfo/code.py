from com.inductiveautomation.ignition.common import BasicDataset
from java.lang import String, Double
import system
from java.util import Calendar
from java.text import SimpleDateFormat
from math import floor
from java.util import Date
from system.dataset import toDataSet, addRow, toPyDataSet
import json




def getShiftData(start, end, tagPath):
    """
    Retrieves, filters, and compiles data for a specific shift.
    Args:
        start (Date): Shift start time.
        end (Date): Shift end time.
        tagPath (str): Path of the tag for querying historical data.
    Returns:
        dataset: A dataset with processed shift recipe runs.
    """
    queryStart = system.date.addHours(start, -1)
    rawDataSet = system.tag.queryTagHistory(paths=[tagPath], startDate=queryStart, endDate=end, returnSize=-1, aggregationMode="Maximum", returnFormat='Wide')

    uniqueDataSet = getUniqueRecipes(rawDataSet)

    compiledShiftRecipeRuns = compileShiftRecipeData(start, end, uniqueDataSet)

    
    return compiledShiftRecipeRuns

def getUniqueRecipes(dataSet):
    """
    Removes consecutive duplicate recipes and swaps the first two columns in a dataset.
    Args:
        dataSet (dataset): The original dataset to process.
    Returns:
        dataset: A new dataset with unique consecutive recipes.
    """
    if not dataSet or dataSet.getRowCount() == 0:
        return dataSet

    headers = [dataSet.getColumnName(i) for i in range(dataSet.getColumnCount())]
    headers[0], headers[1] = headers[1], headers[0]

    uniqueDataSet = toDataSet(headers, [])
    for i in range(dataSet.getRowCount()):
        row = [dataSet.getValueAt(i, col) for col in range(dataSet.getColumnCount())]
        row[0], row[1] = row[1], row[0]

        if i == 0 or row[0] != uniqueDataSet.getValueAt(uniqueDataSet.getRowCount() - 1, 0):
            uniqueDataSet = addRow(uniqueDataSet, row)

    return toPyDataSet(uniqueDataSet)

def compileShiftRecipeData(start, end, filteredDataSet):
    """
    Compiles recipe run data within a shift period.
    Args:
        start (Date): Shift start time.
        end (Date): Shift end time.
        filteredDataSet (dataset): Filtered dataset of recipe changes.
    Returns:
        dataset: A dataset with compiled shift recipe data.
    """
    headers = ["Recipe Name", "Start Time", "End Time", "Duration (Minutes)"]
    shiftData = []
    dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS")

    startStr, endStr = dateFormat.format(start), dateFormat.format(end)
    endTimes = [filteredDataSet.getValueAt(i + 1, 1) if i < filteredDataSet.getRowCount() - 1 else endStr for i in range(filteredDataSet.getRowCount())]

    for i in range(filteredDataSet.getRowCount()):
        recipe, startTime, endTime = filteredDataSet.getValueAt(i, 0), filteredDataSet.getValueAt(i, 1), endTimes[i]
        if startTime < startStr <= endTime:
            startTime = startStr
        if startTime >= startStr:
            duration = calculateMinutesBetweenTimes(startTime, endTime, dateFormat)
            shiftData.append([recipe, startTime, endTime, duration])

    return toDataSet(headers, shiftData)

def calculateMinutesBetweenTimes(start, end, format):
    """
    Calculates the time duration in minutes between two timestamps.
    Args:
        start (str): Start timestamp.
        end (str): End timestamp.
        format (SimpleDateFormat): Format for parsing the timestamps.
    Returns:
        float: Time duration in minutes.
    """
    startTime = format.parse(start)
    endTime = format.parse(end)
    durationMillis = endTime.getTime() - startTime.getTime()
    return round(durationMillis / 60000.0, 2)

def calculateIdleTime(recipeRunsInfo, idlePath):
    """
    Calculates the idle time for each recipe run.
    Args:
        recipeRunsInfo (dataset): The dataset containing recipe runs.
        idlePath (str): The tag path for machine idle status.
    Returns:
        list: List of idle times for each recipe run.
    """
    dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS")
    idleTimes = []

    for i in range(recipeRunsInfo.getRowCount()):
        startStr = recipeRunsInfo.getValueAt(i, "Start Time")
        endStr = recipeRunsInfo.getValueAt(i, "End Time")
        startTime = dateFormat.parse(startStr)
        endTime = dateFormat.parse(endStr)
        idleTimeSeconds = getIdleTimeForRecipe(idlePath, startTime, endTime)
        idleTimeMinutes = round(idleTimeSeconds / 60.0, 2)
        idleTimes.append(idleTimeMinutes)

    return idleTimes

def getIdleTimeForRecipe(idlePath, startTime, endTime):
    """
    Calculate the idle time for the machine during a specific time period.
    Args:
        idlePath (str): The tag path for machine idle status.
        startTime (Date): Start time for the period.
        endTime (Date): End time for the period.
    Returns:
        int: Total idle time in minutes during the period.
    """
    paths = [idlePath]
    durationResult = system.tag.queryTagCalculations(paths, ["DurationOn"], startTime, endTime)
    return int(durationResult.getValueAt(0, 1))

def calculateExpectedParts(recipeRunsInfo, idleTimes):
    """
    Calculates expected parts for each recipe run.
    Args:
        recipeRunsInfo (dataset): The dataset containing recipe runs and idle times.
        idleTimes (list): List of idle times for each recipe run.
    Returns:
        list: List of expected parts for each recipe run.
    """
    expectedPartsList = []

    for i in range(recipeRunsInfo.getRowCount()):
        duration = recipeRunsInfo.getValueAt(i, "Duration (Minutes)")
        setupTime = recipeRunsInfo.getValueAt(i, "Setup Time")
        idleTime = idleTimes[i]
        cycleTarget = recipeRunsInfo.getValueAt(i, "Cycle Target")

        # Calculate expected parts
        rawExpectedParts = (duration - setupTime - idleTime) / cycleTarget
        expectedParts = max(floor(rawExpectedParts), 0)  # Ensuring expectedParts is never less than 0

        expectedPartsList.append(int(expectedParts))  # Convert to integer

    return expectedPartsList

def getRecipeRunInfo(rootTagPath, machineName, start, end):
    """
    Main function to process shift data and calculate expected parts.
    Args:
        recipeTagPath (str): Path of the recipe data.
        idleTagPath (str): Path of the idle tag data.
        start (Date): Start time of the shift.
        end (Date): End time of the shift.
    Returns:
        dataset: Final dataset with additional information.
    """
    idleTagPath = rootTagPath + 'machineStatus/Machine Idle'
    recipeTagPath = rootTagPath + 'Active Recipe'
    # Retrieve and process shift data
    shiftData = getShiftData(start, end, recipeTagPath)

    # Convert the recipe dictionary to a dataset
    databaseRecipeTargets = getRecipeInfoFromDB(machineName)


    # Merge shift data with additional recipe data (setup time and cycle target)
    shiftDataWithAdditionalInfo = mergeShiftDataWithAdditionalInfo(shiftData, databaseRecipeTargets)

    
    
    # Calculate idle times
    idleTimes = calculateIdleTime(shiftDataWithAdditionalInfo, idleTagPath)

    # Calculate expected parts
    expectedParts = calculateExpectedParts(shiftDataWithAdditionalInfo, idleTimes)

    expectedPartsTable =enhanceDataSetWithColumns(shiftDataWithAdditionalInfo, idleTimes, expectedParts)

    
    return expectedPartsTable

def enhanceDataSetWithColumns(dataSet, idleTimes, expectedParts):
    """
    Enhances the dataset with additional columns for idle time and expected parts.
    Args:
        dataSet (dataset): The original dataset.
        idleTimes (list): List of idle times.
        expectedParts (list): List of expected parts.
    Returns:
        dataset: Enhanced dataset.
    """
    columnNames = list(dataSet.getColumnNames()) + ["Idle Time (Minutes)", "Expected Parts"]
    enhancedRows = []

    for i in range(dataSet.getRowCount()):
        row = list(dataSet.getValueAt(i, j) for j in range(dataSet.getColumnCount()))
        row.append(idleTimes[i])
        row.append(expectedParts[i])
        enhancedRows.append(row)

    return toDataSet(columnNames, enhancedRows)
    
def mergeShiftDataWithAdditionalInfo(shiftData, databaseRecipeTargets):
    """
    Merges shift data with additional recipe information.
    Args:
        shiftData (dataset): The dataset containing shift data.
        databaseRecipeTargets (dataset): The dataset containing additional recipe info.
    Returns:
        dataset: Merged dataset.
    """
    # Convert datasets to PyDataSets for easier manipulation
    pyShiftData = toPyDataSet(shiftData)
    pyAdditionalData = toPyDataSet(databaseRecipeTargets)

    # Create a dictionary for quick access to additional data
    additionalDataDict = {row[0]: (row[1], row[2]) for row in pyAdditionalData}

    # Prepare data for the new dataset
    enhancedRows = []
    for row in pyShiftData:
        recipeName = row[0]
        additionalData = additionalDataDict.get(recipeName, (None, None))
        newRow = list(row) + list(additionalData)
        enhancedRows.append(newRow)

    # Define new column names
    newColumnNames = list(shiftData.getColumnNames()) + ["Setup Time", "Cycle Target"]

    # Create and return the new dataset
    return toDataSet(newColumnNames, enhancedRows)
    

def findChildMachines(systemName):
    """
    This function browses the tag structure under a given system name and 
    returns a list of child machine paths excluding any system tags.
    
    :param systemName: The name of the system to browse for child machines.
    :return: A list of child machine paths.
    """

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


def countOn(tagPath, queryStart,queryEnd):
    """
    Performs a CountOn query for a specified tag over a shift.

    :param tagPath: Path of the tag
    :param queryStart: Start time of query
    :return: Result of the CountOn query
    """
    start = queryStart
    end = queryEnd
    paths = [tagPath]
    countResult = system.tag.queryTagCalculations(paths, ["CountOn"], start, end)
    return int(countResult.getValueAt(0, 1))

def durationOn(tagPath, queryStart, queryEnd):
    """
    Performs a DurationOn query for a specified tag over a shift.

    :param tagPath: Path of the tag
    :param queryStart: Start time of query
    :return: Result of the DurationOn query or 0 if None
    """
    start = queryStart
    end = queryEnd
    paths = [tagPath]
    durationResult = system.tag.queryTagCalculations(paths, ["DurationOn"], start, end)
    return durationResult.getValueAt(0, 1) if durationResult is not None else 0

def getRecipeInfoFromDB(machineName):
    """
    Retrieves recipe information from the database for a given machine name.
    
    :param machineName: The name of the machine to query for recipe information.
    :return: A BasicDataset containing the recipe name, setup time, and cycle target.
    """
    # Define the named query path
    queryPath = "scadaGetRecipeTable"
    
    
    targetString = 'Acme Robot'
    if targetString.lower() in machineName.lower():
        machineName = targetString
    
    # Set up the parameters for the query
    queryParams = {"machineName": machineName}
    
    # Run the named query
    result = system.db.runNamedQuery(queryPath, queryParams)
    
    return result

def dictsToDataset(dictList):
    """
    Converts a list of dictionaries to an Ignition dataset.
    
    Args:
        dictList: A list of dictionaries where each dictionary represents a row in the dataset.
    
    Returns:
        A BasicDataset object representing the data.
    """
    
    # Extract the column names from the first dictionary
    if not dictList:
        raise ValueError("dictList is empty or None")
    
    headers = list(dictList[0].keys())
    
    # Prepare the data for the dataset
    data = []
    for rowDict in dictList:
        row = [rowDict[columnName] for columnName in headers]
        data.append(row)
    
    # Define the column types (assuming all data is either String or Double)
    columnTypes = []
    for header in headers:
        if isinstance(dictList[0][header], float):
            columnTypes.append(Double)
        else:
            columnTypes.append(String)
    
    # Create the dataset
    return system.dataset.toPyDataSet(system.dataset.toDataSet(headers, data))


def createTagPaths(systemName, machineName):
    """
    Constructs and returns the tag paths for various machine statuses and operational data.

    :param systemName: The name of the system.
    :param machineName: The name of the machine within the system.
    :return: Dictionary of tag paths.
    """
    rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'

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

def createTagPaths(rootTagPath, machineName):
    """
    Constructs and returns the tag paths for various machine statuses and operational data.

    :param systemName: The name of the system.
    :param machineName: The name of the machine within the system.
    :return: Dictionary of tag paths.
    """
    

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

def writeToTags(tagPathDict, dataDict):
    """
    Writes aggregated data to the system tags.

    :param tagPathDict: Dictionary of tag paths.
    :param dataDict: Dictionary containing the data to be written to each tag.
    """
    for tag, value in dataDict.items():
        tagPath = tagPathDict.get(tag)
        if tagPath:
            system.tag.write(tagPath, value)

def getActiveRecipes(tagPath, machineName, activeRecipes):
    """
    Retrieves and processes recipe information for a given machine and appends to the active recipes list.

    :param tagPath: The tag path for the active recipe.
    :param machineName: The name of the machine.
    :param activeRecipes: List to append the active recipe data.
    """
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




def main(systemNames, shiftStartHours):
    """
    Queries tag history for multiple systems and performs data aggregation on Historical Tag Paths.
    
    Args:
        systemNames: A list of system names to query.
        shiftStartHours: List of hours at which the shift starts.
    """

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
            recipeRunData = getRecipeRunInfo(rootTagPath, machineName, queryStart, queryEnd)

            # Calculate the total expected parts from the recipe run data
            expectedPartsIndex = recipeRunData.getColumnIndex("Expected Parts")
            totalExpectedParts = sum(recipeRunData.getValueAt(row, expectedPartsIndex) for row in range(recipeRunData.getRowCount()))

            # Count completed parts within the shift
            partsComplete = countOn(tagPaths['cycleDone'], queryStart, queryEnd)
            # Ensure partsComplete is a number, if not set it to 0
            if not isinstance(partsComplete, (int, float)):
                partsComplete = 0
            
            # Calculate idle time in minutes for the shift
            shiftIdleTime = round(durationOn(tagPaths['idle'], queryStart, queryEnd) / 60.0, 2)
            # Ensure shiftIdleTime is a number, if not set it to 0
            if not isinstance(shiftIdleTime, (int, float)):
                shiftIdleTime = 0
            
            # Calculate run time in minutes for the shift
            shiftRunTime = round(durationOn(tagPaths['inCycle'], queryStart, queryEnd) / 60.0, 2)
            # Ensure shiftRunTime is a number, if not set it to 0
            if not isinstance(shiftRunTime, (int, float)):
                shiftRunTime = 0
            
            # Calculate total time in minutes from shift start to current time
            timeDifferenceInMinutes = round((end.getTime() - shiftStartTime.getTime()) / 60000.0, 2)
           
          
            # If partsComplete is greater than 0, shiftIdleTime is 0, and shiftRunTime is 0,
            # then calculate shiftRunTime based on parts completion ratio
            if partsComplete > 0 and shiftIdleTime == 0 and shiftRunTime == 0:
            	
                try:
						# Calculate score and round to one decimal place
                        score = round(float(partsComplete)/float(totalExpectedParts),1)
                        
                        # Constrain score between 0 and 1
                        score = max(0, min(score, 1))

                        shiftRunTime = round(timeDifferenceInMinutes * score,1)
                        
                except Exception as e:
                    # Handle the exception (e.g., log it, set shiftRunTime to a default value, etc.)
                    print 'adjusting error'
                    shiftRunTime = 0
            
            # Determine downtime by subtracting idle and run time from total time
            shiftDownTime = timeDifferenceInMinutes - shiftIdleTime - shiftRunTime
            print ''

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

        # Identify the machine with the highest cycle target (pace setter)
        paceSetter = max(activeRecipes, key=lambda x: x['CycleTarget'])
        json_string = json.dumps(paceSetter)
        systemRecipeTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/_ System/Active Recipe Info"
        systemCycleDoneTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/_ System/machineStatus/Cycle Done"
        systemScorecardTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/_ System/Scorecard Value"
        system.tag.write(systemRecipeTagPath, json_string)
        
        # Define a dictionary for tagPaths if it's intended to be used that way
        tagPaths = {
            "systemCycleDoneTagPath": systemCycleDoneTagPath,
            "systemScorecardTagPath": systemScorecardTagPath
        }
        
        # Assuming Utility.countOn and scadaOverview.getSystemExpectedParts.main are predefined functions
        # You will also need to define 'queryStart' and 'queryEnd' if they are not defined yet
        systemPartsComplete = countOn(tagPaths["systemCycleDoneTagPath"], queryStart, queryEnd)
        # Assuming shiftStartTime and end are datetime objects
        timeDifference = end.getTime() - shiftStartTime.getTime()  # This gives difference in milliseconds
        
        # Convert milliseconds to hours
        hoursDifference = timeDifference / (1000.0 * 60 * 60)
        systemExpectedParts = round(hoursDifference*60,0)
        

        # Calculate and print system score
        systemScore = int(round((float(systemPartsComplete) / systemExpectedParts) * 100, 0))
        system.tag.write(systemScorecardTagPath, systemScore)
 	    
def example():
	#scadaOverview.combinedFunctionsForMachineData_Jan11th.updateMachineInfo(systemNames, shiftStartHours)
	systemNames = ['SimulationV2']
	shiftStartHours = [6,8,18]
	main(systemNames, shiftStartHours)

