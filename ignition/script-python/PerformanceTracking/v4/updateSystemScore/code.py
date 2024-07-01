from com.inductiveautomation.ignition.common import BasicDataset
from java.lang import String, Double
import system
from java.util import Calendar
from java.text import SimpleDateFormat
from math import floor
from java.util import Date
from system.dataset import toDataSet, addRow, toPyDataSet
import json

def sortedMachinePaths(browsePath):
    """
    Retrieves and sorts machine paths based on machine position.

    Args:
        browsePath: The path to browse for machine paths.

    Returns:
        A list of machine paths sorted by machine position, filtered to include only those with the maximum integer part.
    """
    results = system.tag.browse(browsePath)
    paths = []  # Create an empty list to store the paths

    # Collect machine paths
    for result in results.getResults():
        fullPathStr = str(result['fullPath'])  # Convert to string
        filteredFullPath = fullPathStr.replace(browsePath, "")  # Remove browsePath
        
        # Remove leading '/' if present
        if filteredFullPath.startswith('/'):
            filteredFullPath = filteredFullPath[1:]
    
        # Only add if it's not '_ System'
        if filteredFullPath != '_ System':
            paths.append(filteredFullPath)
    
    # Read machinePosition for each path and store in a list
    pathsWithPosition = []
    for path in paths:
        machinePositionPath = browsePath + '/' + path + '/Parameters.machinePosition'
        machinePosition = system.tag.read(machinePositionPath).value
        
        # Ensure machinePosition is a float
        if machinePosition is not None:
            try:
                machinePosition = float(machinePosition)
                pathsWithPosition.append((path, machinePosition))
            except ValueError:
                pass  # Skip if conversion to float fails
    
    # Sort paths by machinePosition
    pathsWithPosition.sort(key=lambda x: x[1])
    sortedPaths = [path[0] for path in pathsWithPosition]
    
    # Find the maximum integer part of machinePosition
    maxIntPart = max(int(floor(pos)) for _, pos in pathsWithPosition)
    
    # Filter paths to include only those with the maximum integer part
    filteredPaths = [path for path, pos in pathsWithPosition if int(floor(pos)) == maxIntPart]

    return filteredPaths

def getExpectedparts(startTime, endTime, systemName):
    """
    Calculates the expected parts based on the duration between startTime and endTime.

    Args:
        startTime: The start time for the calculation.
        endTime: The end time for the calculation.
        systemName: The name of the system being calculated.
    """
    
    durationMillis = float(endTime.getTime() - startTime.getTime())  # Calculate duration in milliseconds
    hours = (durationMillis / (1000 * 60 * 60))  # Convert milliseconds to hours
    # Calculate expected parts based on hours (adjust logic as needed)
    expectedParts = int(round((60 * hours), 0))
    return expectedParts

def main(startTime, endTime, systemName):
    """
    Updates system tags with the sorted machine paths for a specific system.
    
    Args:
        startTime: The start time for the update.
        endTime: The end time for the update.
        systemName: The name of the system to update.
    """
    rootPath = '[SCADA Overview]Performance Tracking/'
    systemPath = rootPath + systemName

    # Get sorted machine paths
    endMachines = sortedMachinePaths(systemPath)
    partsDone = []

    # Collect parts complete for each machine
    for machine in endMachines:
        partsCompleteTagPath = systemPath + '/' + machine + '/Parts Complete'
        partsComplete = system.tag.read(partsCompleteTagPath).value
        partsDone.append(partsComplete)
    
    totalPartsDone = sum(partsDone)

    # Calculate expected parts
    expectedParts = getExpectedparts(startTime, endTime, systemName)

    # Calculate scorecard value, ensuring float division
    if expectedParts != 0:
        scorecardValue = round((float(totalPartsDone) / float(expectedParts)) * 100, 0)
    else:
        scorecardValue = 0  # Handle division by zero
    
    # Write calculated values to tags
    system.tag.write(systemPath + '/_ System/Completed Parts', totalPartsDone)
    system.tag.write(systemPath + '/_ System/Expected Parts', expectedParts)
    system.tag.write(systemPath + '/_ System/Scorecard Value', scorecardValue)

    return