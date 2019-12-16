import json
import logging
import boto3

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

def fulfill(event): # All three slots should be valid - matching to an account - and now the user has been validated.
    return close(event['sessionAttributes'], 'Fulfilled', 'Thanks.')
    
def goodDOB(event):
    slots = get_slots(event)
    DOB = slots['DOB']
    if (DOB == None): # If the slot isn't filled it obviously can't be good.
        return False
    else:
        bucket = 'connect-499d41f81250'
    key = 'telephony/accounts.json'
    
    s3 = boto3.client('s3')
    try:
        data = s3.select_object_content(
            Bucket = bucket, 
            Key = key,
            ExpressionType = "SQL",
            Expression = "Select * from s3object s where s.accountNumber = {}".format(slots['accountNumber']),
            InputSerialization = {"JSON": {"Type": "document"}},
            OutputSerialization = {"JSON": {}})
        for event in data['Payload']:
            if 'Records' in event:
                account = event['Records']['Payload'].decode('utf-8')
                account = json.loads(account)
                if (str(account['DOB']) == str(slots['DOB'])):
                    return True
        return False
            
    except Exception as e:
        print (e)
        raise e

def authenticateDOB(event):
    source = event['invocationSource']
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        if (slots['DOB'] != None): 
            if not (goodDOB(event)): # Checks if the DOB given matches the account's DOB.
                return elicit_slot(event['sessionAttributes'], 
                            event['currentIntent']['name'],
                            slots,
                            "DOB",
                            "Sorry, that date of birth did not match our records. Please give me your date of birth.") 
            else:
                return fulfill(event) # Good DOB means the user has provided all three requirements and has been validated.
        else:
            return delegate(event['sessionAttributes'], slots) # If the slot isn't filled, let Lex prompt for it.
            
            

def authenticateSSN(event):
    source = event['invocationSource']
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        if (slots['SSN'] != None): # Slot is filled so we check if it's 9-digits long and if the SSN matches the account number's SSN.
            if (len(str(slots['SSN'])) != 9):
                return elicit_slot(event['sessionAttributes'], 
                            event['currentIntent']['name'],
                            slots,
                            "SSN",
                            "I'm sorry, that was not a 9-digit number. Please give me your 9-digit Social Security Number used to open this account.")
            if not goodSSN(event): 
                return elicit_slot(event['sessionAttributes'], 
                            event['currentIntent']['name'],
                            slots,
                            "SSN",
                            "Sorry, that did not match our records. Please give me your 9-digit Social Security Number used to open this account.")
            return delegate(event['sessionAttributes'], slots) # If the SSN is good, let Lex prompt for the next slot - DOB.
        return delegate(event['sessionAttributes'], slots) #If our slot isn't filled, let Lex prompt for SSN.

def authenticateAccountNumber(event):
    source = event['invocationSource']
    if source == 'DialogCodeHook':
        slots = get_slots(event)
        if (event['currentIntent']['slots']['accountNumber'] != None): # This branch is taken once actual input for the accountNumber slot has been given.
            accountNum = event['currentIntent']['slots']['accountNumber']
            # Input validation for the account number.
            if (len(str(accountNum)) != 13):                # If the length of the account number that was given is not 13, elicit for the accountNumber slot again.
                return elicit_slot(event['sessionAttributes'], 
                        event['currentIntent']['name'],
                        slots,
                        "accountNumber",
                        "I'm sorry, that was not a 13-digit number. Please give me your 13 digit account number. This number appears at the top of your statement.")
            if not (goodAccountNum(accountNum)): # Checking the hardcoded accounts for the 13-digit number entered.
                return elicit_slot(event['sessionAttributes'], 
                        event['currentIntent']['name'],
                        slots,
                        "accountNumber",
                        "I'm sorry, that account number was not found in our system. Please give me your 13 digit account number.")
            
            return delegate(event['sessionAttributes'], slots) # If the input is valid, begin to elicit for the user's SSN. Delegate will let the Lex bot prompt for the next slot.
        else:
            return delegate(event['sessionAttributes'], slots) # If the slot hasn't been filled, let Lex prompt for the slot.

def goodAccountNum(acc):
    bucket = 'connect-499d41f81250'
    key = 'telephony/accounts.json'
    
    s3 = boto3.client('s3')
    try:
        data = s3.select_object_content(
            Bucket = bucket, 
            Key = key,
            ExpressionType = "SQL",
            Expression = "Select * from s3object s where s.accountNumber = {}".format(acc),
            InputSerialization = {"JSON": {"Type": "document"}},
            OutputSerialization = {"JSON": {}})
        for event in data['Payload']:
            if 'Records' in event:
                records = event['Records']['Payload'].decode('utf-8')
                return True
        return False
            
    except Exception as e:
        print (e)
        raise e

def goodSSN(event): # This function checks if the SSN is matching with the account number's SSN.
    slots = get_slots(event)
    bucket = 'connect-499d41f81250'
    key = 'telephony/accounts.json'
    
    s3 = boto3.client('s3')
    try:
        data = s3.select_object_content(
            Bucket = bucket, 
            Key = key,
            ExpressionType = "SQL",
            Expression = "Select * from s3object s where s.accountNumber = {}".format(slots['accountNumber']),
            InputSerialization = {"JSON": {"Type": "document"}},
            OutputSerialization = {"JSON": {}})
        for event in data['Payload']:
            if 'Records' in event:
                account = event['Records']['Payload'].decode('utf-8')
                account = json.loads(account)
                if (str(account['SSN']) == str(slots['SSN'])):
                    return True
        return False
            
    except Exception as e:
        print (e)
        raise e

def dispatch(event):
    logger.debug(json.dumps(event))
    slots = get_slots(event)
    source = event['invocationSource']
    if (source == 'DialogCodeHook'):
        if (slots['accountNumber'] == None): # If our slots are NOT filled, we will delegate so that Lex can prompt the user. 
            return delegate(event['sessionAttributes'], slots) 
        if not (goodAccountNum(slots['accountNumber'])): # If our slot IS filled, we authenticate the input until it is good by checking for a match via the account number.
            return authenticateAccountNumber(event)
            
        event['sessionAttributes'] = { 
            "accountNumber" : slots['accountNumber']
            } # This sets our session attribute for the account number.
            
        if (slots['SSN'] == None): # These next two blocks are the same as the first just specialized to deal with the SSN and DOB input.
            return delegate(event['sessionAttributes'], slots) 
        if not (goodSSN(event)):
            return authenticateSSN(event)
            
        if (slots['DOB'] == None): 
            return delegate(event['sessionAttributes'], slots) 
        if not (goodDOB(event)):
            return authenticateDOB(event)
        return fulfill(event)
    else:
        return fulfill(event)
            
            
