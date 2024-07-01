import system
from java.text import SimpleDateFormat

def insertRecipeRunData(recipeRunData, machineUniqueName):
    print("\nStarting to process the insert operation for recipe run data.")
    
    # Create SimpleDateFormat to handle date parsing and formatting
    dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS")
    
    print("\nDataset Column Names and Types:")
    for col in range(recipeRunData.getColumnCount()):
        print("  Column {}: {} ({})".format(col, recipeRunData.getColumnName(col), recipeRunData.getColumnType(col)))
    
    for row in range(recipeRunData.getRowCount()):
        recipeName = recipeRunData.getValueAt(row, "Recipe Name")
        startTime = dateFormat.parse(recipeRunData.getValueAt(row, "Start Time"))
        endTime = dateFormat.parse(recipeRunData.getValueAt(row, "End Time"))
        startTimeStr = dateFormat.format(startTime)
        endTimeStr = dateFormat.format(endTime)


        params = {
            "MachineName": machineUniqueName,
            "RecipeName": recipeName,
            "StartTime": startTimeStr,
            "EndTime": endTimeStr,
            "DurationMinutes": recipeRunData.getValueAt(row, "Duration (Minutes)"),
            "SetupTime": recipeRunData.getValueAt(row, "Setup Time"),
            "CycleTarget": recipeRunData.getValueAt(row, "Cycle Target"),
            "IdleTimeMinutes": recipeRunData.getValueAt(row, "Idle Time (Minutes)"),
            "ExpectedParts": recipeRunData.getValueAt(row, "Expected Parts")
        }
        
        # Print values for debugging
        print("\nExecuting upsert with parameters:", params)
        # Running the named query with parameters
        system.db.runNamedQuery("SCADA_Overview/UpsertRecipeRunData", params)

    print("\nInsert/upsert operation completed.")

def main(recipeRunData, systemName, machineName):
    print("\nProcessing recipe run data.")
    Utility.printAsTable(recipeRunData)
    machineUniqueName = systemName + '/' + machineName
    insertRecipeRunData(recipeRunData, machineUniqueName)
    print("\nData processing complete.")
    print ''
    print ''

# Example usage:
# Assuming 'recipeRunData' is your dataset with the required structure.
# main(recipeRunData, "SystemXYZ", "Machine123")