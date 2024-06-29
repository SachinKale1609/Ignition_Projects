UPDATE  RecipeRunTargets 
SET  LineName =:LineName,
Machinename =:MachineName,
RecipeName =:RecipeName,
CycleTarget =:CycleTarget,
SetupTime =:SetupTime
Where  RecipeID =:RecipeID
 