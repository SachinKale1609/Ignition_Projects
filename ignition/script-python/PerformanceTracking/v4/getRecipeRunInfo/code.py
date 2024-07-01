from com.inductiveautomation.ignition.common import BasicDataset
from java.lang import String, Double
import system
from java.util import Calendar, Date
from java.text import SimpleDateFormat
from math import floor
from system.dataset import toDataSet, addRow, toPyDataSet
import json

def getRecipeRunsFromHistorian(start, end, tagPath):
    """
    Retrieves, filters, and compiles data for a specific shift.
    Args:
        start (Date): Shift start time.
        end (Date): Shift end time.
        tagPath (str): Path of the tag for querying historical data.
    Returns:
        dataset: A dataset with processed shift recipe runs.
    """
    try:
        queryStart = start
        rawDataSet = system.tag.queryTagHistory(paths=[tagPath], startDate=queryStart, endDate=end, returnSize=-1, aggregationMode="Maximum", returnFormat='Wide')
   
        uniqueDataSet = getUniqueRecipes(rawDataSet)

        compiledShiftRecipeRuns = compileShiftRecipeData(start, end, uniqueDataSet)
        
        
    
        return compiledShiftRecipeRuns
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getRecipeRunsFromHistorian: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getRecipeRunsFromHistorian', 'Error2': 'Error while processing shift data', 'Error3': str(e)})

def getUniqueRecipes(dataSet):
    """
    Removes consecutive duplicate recipes and swaps the first two columns in a dataset.
    Args:
        dataSet (dataset): The original dataset to process.
    Returns:
        dataset: A new dataset with unique consecutive recipes.
    """
    try:
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
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getUniqueRecipes: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getUniqueRecipes', 'Error2': 'Error while removing duplicates', 'Error3': str(e)})

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
    try:
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
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in compileShiftRecipeData: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.compileShiftRecipeData', 'Error2': 'Error while compiling shift data', 'Error3': str(e)})
        


def machineNameRecipeBias(machineName):
	
	targetString = 'Acme Robot'
	if targetString.lower() in machineName.lower():
		machineName = targetString
		
	return machineName

def getRecipeInfoFromDB(machineName):
    """
    Retrieves recipe information from the database for a given machine name.
    
    :param machineName: The name of the machine to query for recipe information.
    :return: A BasicDataset containing the recipe name, setup time, and cycle target.
    """
    try:
        # Define the named query path
        queryPath = "scadaGetRecipeTable"
        originalMachineName = machineName
        machineName = machineNameRecipeBias(originalMachineName)

    
        # Set up the parameters for the query
        queryParams = {"machineName": machineName}
    
        # Run the named query
        result = system.db.runNamedQuery(queryPath, queryParams)
    
        return result
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getRecipeInfoFromDB: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getRecipeInfoFromDB', 'Error2': 'Error retrieving recipe information from database', 'Error3': str(e)})




def dictsToDataset(dictList):
    """
    Converts a list of dictionaries to an Ignition dataset.
    
    Args:
        dictList: A list of dictionaries where each dictionary represents a row in the dataset.
    
    Returns:
        A BasicDataset object representing the data.
    """
    try:
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
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in dictsToDataset: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.dictsToDataset', 'Error2': 'Error converting dictionaries to dataset', 'Error3': str(e)})        
        


def mergeShiftDataWithAdditionalInfo(shiftData, databaseRecipeTargets):
    """
    Merges shift data with additional recipe information, using default values when specific recipe info is missing.
    Args:
        shiftData (dataset): The dataset containing shift data.
        databaseRecipeTargets (dataset): The dataset containing additional recipe info.
    Returns:
        dataset: Merged dataset.
    """
    try:
        # Convert datasets to PyDataSets for easier manipulation
        pyShiftData = toPyDataSet(shiftData)
        pyAdditionalData = toPyDataSet(databaseRecipeTargets)
    
        # Create a dictionary for quick access to additional data, and extract the default values
        defaultValues = None
        additionalDataDict = {}
        for row in pyAdditionalData:
            recipeName, setupTime, cycleTarget = row[0], row[1], row[2]
            additionalDataDict[recipeName] = (setupTime, cycleTarget)
            if recipeName == 'default':
                defaultValues = (setupTime, cycleTarget)
    
        # Prepare data for the new dataset
        enhancedRows = []
        for row in pyShiftData:
            recipeName = row[0]
            additionalData = additionalDataDict.get(recipeName, defaultValues)
            newRow = list(row) + list(additionalData)
            enhancedRows.append(newRow)
    
        # Define new column names
        newColumnNames = list(shiftData.getColumnNames()) + ["Setup Time", "Cycle Target"]
    
        # Create and return the new dataset
        return toDataSet(newColumnNames, enhancedRows)
    
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in mergeShiftDataWithAdditionalInfo: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.mergeShiftDataWithAdditionalInfo', 'Error2': 'Error merging shift data', 'Error3': str(e)})



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
    try:
        startTime = format.parse(start)
        endTime = format.parse(end)
        durationMillis = endTime.getTime() - startTime.getTime()
        return round(durationMillis / 60000.0, 2)
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in calculateMinutesBetweenTimes: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.calculateMinutesBetweenTimes', 'Error2': 'Error calculating duration between times', 'Error3': str(e)})





def calculateIdleTime(recipeRunsInfo, idlePath):
    """
    Calculates the idle time for each recipe run.
    Args:
        recipeRunsInfo (dataset): The dataset containing recipe runs.
        idlePath (str): The tag path for machine idle status.
    Returns:
        list: List of idle times for each recipe run.
    """
    try:
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
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in calculateIdleTime: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.calculateIdleTime', 'Error2': 'Error calculating idle time', 'Error3': str(e)})




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
    try:
        paths = [idlePath]
        durationResult = system.tag.queryTagCalculations(paths, ["DurationOn"], startTime, endTime)
        return int(durationResult.getValueAt(0, 1))
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getIdleTimeForRecipe: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getIdleTimeForRecipe', 'Error2': 'Error during idle time calculation', 'Error3': str(e)})

def calculateExpectedParts(recipeRunsInfo, idleTimes, rootTagPath):
    """
    Calculates expected parts for each recipe run.
    Args:
        recipeRunsInfo (dataset): The dataset containing recipe runs and idle times.
        idleTimes (list): List of idle times for each recipe run.
    Returns:
        list: List of expected parts for each recipe run.
    """
    try:
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
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in calculateExpectedParts: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.calculateExpectedParts', 'Error2': 'Error calculating expected parts', 'Error3': str(e)})


def enhanceDataSetWithColumns(dataSet, idleTimes, expectedParts, rootTagPath):
    """
    Enhances the dataset with additional columns for idle time and expected parts.
    Args:
        dataSet (dataset): The original dataset.
        idleTimes (list): List of idle times.
        expectedParts (list): List of expected parts.
    Returns:
        dataset: Enhanced dataset.
    """
    try:
        columnNames = list(dataSet.getColumnNames()) + ["Idle Time (Minutes)", "Expected Parts"]
        enhancedRows = []
    
        for i in range(dataSet.getRowCount()):
            row = list(dataSet.getValueAt(i, j) for j in range(dataSet.getColumnCount()))
            row.append(idleTimes[i])
            row.append(expectedParts[i])
            enhancedRows.append(row)
    
        return toDataSet(columnNames, enhancedRows)
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in enhanceDataSetWithColumns: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.enhanceDataSetWithColumns', 'Error2': 'Error enhancing dataset', 'Error3': str(e)})


                



def main(systemName, machineName, start, end):
    """
    Main function to process shift data and calculate expected parts.
    Args:
        rootTagPath (str): Path of the recipe data.
        machineName (str): Name of the machine.
        start (Date): Start time of the shift.
        end (Date): End time of the shift.
    Returns:
        dataset: Final dataset with additional information.
    """
    try:
    
    
    	rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
        idleTagPath = rootTagPath + 'machineStatus/Machine Idle'
        recipeTagPath = rootTagPath + 'Active Recipe'
        # Retrieve and process shift data
        shiftData = getRecipeRunsFromHistorian(start, end, recipeTagPath)
    
        # Convert the recipe dictionary to a dataset
        databaseRecipeTargets = getRecipeInfoFromDB(machineName)
    
    
        # Merge shift data with additional recipe data (setup time and cycle target)
        shiftDataWithAdditionalInfo = mergeShiftDataWithAdditionalInfo(shiftData, databaseRecipeTargets)
    
    
        # Calculate idle times
        idleTimes = calculateIdleTime(shiftDataWithAdditionalInfo, idleTagPath)
    
        # Calculate expected parts
        expectedParts = calculateExpectedParts(shiftDataWithAdditionalInfo, idleTimes, rootTagPath)
    
        expectedPartsTable = enhanceDataSetWithColumns(shiftDataWithAdditionalInfo, idleTimes, expectedParts, rootTagPath)
    
    
        return expectedPartsTable
    
    except Exception as e:
        logger = system.util.getLogger("Exception_Error")
        logger.error("ScriptError in getRecipeRunInfo: " + str(e))
        system.db.runNamedQuery('Exception_Error/Exception', {'Error1': 'SCADAOVERVIEW/updateMachineInfo.getRecipeRunInfo', 'Error2': 'Error processing recipe run info', 'Error3': str(e)})
        
        

	
def diagnostic(systemName, machineName, start, end):
    """
    Main function to process shift data and calculate expected parts.
    Args:
        rootTagPath (str): Path of the recipe data.
        machineName (str): Name of the machine.
        start (Date): Start time of the shift.
        end (Date): End time of the shift.
    Returns:
        dataset: Final dataset with additional information.
    """

    
    rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
    print("Starting main function")
    print("rootTagPath: {}".format(rootTagPath))
    print("machineName: {}".format(machineName))
    print("Shift start time: {}".format(start))
    print("Shift end time: {}".format(end))
    
    idleTagPath = rootTagPath + 'machineStatus/Machine Idle'
    rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
    recipeTagPath = rootTagPath + 'Active Recipe'
    print("\nidleTagPath: {}".format(idleTagPath))
    print("recipeTagPath: {}".format(recipeTagPath))
            
                    
    print "\nRetrieving Shift Recipe Run Data From"
    recipeRunDataFromDB = PerformanceTracking.v4.retrieveRecipeRunDB.main(rootTagPath, machineName, start, end)
    print ''
    print type(start)
    optmizedStart = PerformanceTracking.v4.retrieveRecipeRunDB.getMaxEndTime(recipeRunDataFromDB)
    
    if optmizedStart is not None:
	    start = optmizedStart
    
    else:
    	start = system.date.addHours(start, -1)
    
    
    rootTagPath = "[SCADA Overview]Performance Tracking/" + systemName + "/" + machineName + '/'
    print("Starting main function")
    print("rootTagPath: {}".format(rootTagPath))
    print("machineName: {}".format(machineName))
    print("Shift start time: {}".format(start))
    print("Shift end time: {}".format(end))

    
    
    print "\nRetrieving Shift Recipe Run Data From"
    recipeRunDataFromDB = PerformanceTracking.v4.retrieveRecipeRunDB.main(rootTagPath, machineName, start, end)
    
    
    # Retrieve and process shift data
    shiftData = getRecipeRunsFromHistorian(start, end, recipeTagPath)
    print("\nShift data retrieved from historian")
    Utility.printAsTable(shiftData )
    
    # Convert the recipe dictionary to a dataset
    databaseRecipeTargets = getRecipeInfoFromDB(machineName)
    print("Database recipe targets retrieved")
    print("databaseRecipeTargets: {}".format(databaseRecipeTargets))
    
    # Merge shift data with additional recipe data (setup time and cycle target)
    shiftDataWithAdditionalInfo = mergeShiftDataWithAdditionalInfo(shiftData, databaseRecipeTargets)
    print("Shift data merged with additional recipe info")
    Utility.printAsTable(shiftDataWithAdditionalInfo)
    
    # Calculate idle times
    idleTimes = calculateIdleTime(shiftDataWithAdditionalInfo, idleTagPath)
    print("\nIdle times calculated")
    for idleTime in idleTimes:
    	print idleTime
    
    # Calculate expected parts
    expectedParts = calculateExpectedParts(shiftDataWithAdditionalInfo, idleTimes, rootTagPath)
    print("Expected parts calculated")
    for expectedPart in expectedParts:
    	print expectedPart
    
    # Enhance dataset with idle times and expected parts
    expectedPartsTable = enhanceDataSetWithColumns(shiftDataWithAdditionalInfo, idleTimes, expectedParts, rootTagPath)
    print("\nDataset enhanced with idle times and expected parts")
    Utility.printAsTable(expectedPartsTable)
    
    print("\nMain function completed")
    return expectedPartsTable
    
def example(subtractHours):
	systemName = 'SimulationV2'
	machineName = 'Machine 1'
	end = system.date.now()
	print end
	start = system.date.addHours(end, subtractHours)
	print start
	dataSet = diagnostic(systemName, machineName, start, end)
	Utility.printAsTable(dataSet)
	return
	
	