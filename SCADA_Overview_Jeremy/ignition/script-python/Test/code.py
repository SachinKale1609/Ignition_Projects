import java.lang.Exception

def test(): 
# We start with a value, which could represent some user input.
	x = 0
 
# We use that value in our try block, and have a simple print statement if there is an error.
	try:
    		value = 100/x
    		print value
	except :
			Error1 = 'SCADAOVERVIEW'
			Error2 = 'lineno 26'
			Error3 = '3'
			result =system.db.runNamedQuery('Exception Handling/Exception',{'Error1':Error1,'Error2':Error2, 'Error3':Error3 })
			print Error1
			print Error2
			print Error3
			logger = system.util.getLogger("Exception_Error")
			logger.info("ScriptError:Project Library>Test> Line 9")