import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    return dispatch(event)



""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': {
                'contentType': 'PlainText',
                'content': message
            }
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': {
                'contentType': 'PlainText',
                'content': message
            }
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
    
""" For Intents """

def authenticateDOB(event):
    logger.debug(json.dumps(event)) 
   
    source = event['invocationSource']
    
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        if (event['currentIntent']['slots']['DOB'] != None):
            DOB = slots['DOB']
            parts = DOB.split('-')
            year = DOB[0]
            month = DOB[1]
            day = DOB[2]
            msg = "Your birthday is {} {} {}".format(month, day, year)
            return close(event['sessionAttributes'], 'Fulfilled', msg)
        else:
            return close(event['sessionAttributes'], 'Fulfilled', msg)
    else:
        DOB = event['currentIntent']['slots']['DOB']
        parts = DOB.split('-')
        year = parts[0]
        month = parts[1]
        day = parts[2]
        return close(event['sessionAttributes'], 'Fulfilled', "Your birthday is {} {} {}".format(month, day, year))
            
            

def authenticateSSN(event):
    logger.debug(json.dumps(event)) 
   
    source = event['invocationSource']
    print('authenticating')
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        if (len(str(event['currentIntent']['slots']['SSN'])) != 9 and event['currentIntent']['slots']['SSN'] != None):
            return elicit_slot(event['sessionAttributes'], 
                        event['currentIntent']['name'],
                        slots,
                        "SSN",
                        "Sorry, that was not valid. Please enter your 9 digit Social Security Number used to open this account.")
        else:
            return delegate(event['sessionAttributes'], slots)

def authenticateAccountNumber(event):
    logger.debug(json.dumps(event)) 
   
    source = event['invocationSource']
    
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        # if (event['currentIntent']['slots']['SSN'] != None):
        #     return authenticateSSN(event)
        if (event['currentIntent']['slots']['accountNumber'] != None):
            accountNum = event['currentIntent']['slots']['accountNumber']
            # Input validation for the account number.
            if (len(str(accountNum)) != 13):
                return elicit_slot(event['sessionAttributes'], 
                        event['currentIntent']['name'],
                        slots,
                        "accountNumber",
                        "I'm sorry, that was not valid. Please enter your 13 digit account number. This number appears at the top of your statement.")
            else:
                return delegate(event['sessionAttributes'], slots) # If the input is valid, begin to elicit for the user's SSN. Delegate will let the Lex bot prompt for the next slot.
        else:
                return delegate(event['sessionAttributes'], slots) # If the slot hasn't been filled, let Lex prompt for the slot.
                
def dispatch(event):
    intent_name = event['currentIntent']['name']
    slots = get_slots(event)
    if (intent_name == 'account'):
        source = event['invocationSource']
        if source == "FulfillmentCodeHook":
            return authenticateDOB(event)
        if(slots['accountNumber'] == None or (len(str(event['currentIntent']['slots']['accountNumber'])) != 13)):
            return authenticateAccountNumber(event)
        if(event['currentIntent']['slots']['SSN'] == None or len(str(event['currentIntent']['slots']['accountNumber'] != 9))):
            return authenticateSSN(event)
        if(event['currentIntent']['slots']['DOB'] == None):
            return authenticateDOB(event)
        
    

    
    raise Exception('Intent ' + intent_name + ' not supported.')
