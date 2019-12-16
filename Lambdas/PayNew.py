import json
import boto3

def lambda_handler(event, context):
    return dispatch(event)
    
class Account: # Class for accounts.
    def __init__(self, accountNumber, SSN, DOB):
        self.accountNumber = accountNumber
        self.SSN = SSN
        self.DOB = DOB
        
class PayInfo: # Class for the payment information of a specific user
    def __init__(self, accountNumber, date, amount, balance):
        self.accountNumber = accountNumber
        self.date = date
        self.amount = amount
        self.balance = balance


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
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
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

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


""" --- Helper Functions --- """

#subtracts paymentAmount from the loan balance and updates in s3
def changeAccountValue(event):
    slots = get_slots(event)
    
    #load s3 object
    accountNumber = event['sessionAttributes'].get('accountNumber')
    bucket = 'connect-499d41f81250'
    key = 'telephony/accounts.json'
    s3 = boto3.client('s3')
    s3obj = s3.get_object(Bucket=bucket,Key=key)
    serializedObject = s3obj['Body'].read().decode('utf-8')
    #format for loading as json
    serializedObject = '[' + serializedObject.replace("}{", "},{").replace("'", "\"") + ']'
    jsonLoadedObject = json.loads(serializedObject)
    
    #calculate new loan balance and modify json string with new balance
    newBalance = round(float(event['sessionAttributes']['balance']) - float(slots['paymentAmount']),2)
    print("about to find")
    for jObj in jsonLoadedObject:
        print(jObj['accountNumber'])
        if str(jObj['accountNumber']) == str(accountNumber):
            jObj['balance']= newBalance
            print("newbal:"+str(jObj['balance']))
            print("found")
            break
    
    #format json to match standard
    s3Data = str(jsonLoadedObject).replace("}, {", "}{").replace("[","").replace("]","").replace("'", "\"");

    #update s3 balance
    s3.put_object(Bucket=bucket,Key=key,Body=s3Data)
    
    #update session balance
    event['sessionAttributes']['balance'] = str(newBalance)
    
    
#returns a PayInfo object with loan information for accountNumber session attribute 
def getPaymentInfo(event):
    
    #testing purposes
    if event['sessionAttributes'].get('accountNumber') == None: 
        event['sessionAttributes']['accountNumber'] = '4231836184854'

    
    accountNumber = event['sessionAttributes'].get('accountNumber')
    bucket = 'connect-499d41f81250'
    key = 'telephony/accounts.json'
    s3 = boto3.client('s3')
    
    data = s3.select_object_content(
        Bucket = bucket, 
        Key = key,
        ExpressionType = "SQL",
        Expression = "Select s.balance, s.scheduledAmount, s.scheduledDate  from s3object s where s.accountNumber = {}".format(event['sessionAttributes'].get('accountNumber')),
        InputSerialization = {"JSON": {"Type": "document"}},
        OutputSerialization = {"JSON": {}})
    for events in data['Payload']:
        if 'Records' in events:
            jsonResult = json.loads(events['Records']['Payload'].decode('utf-8'))
            print(json.dumps(jsonResult))
            balance = str(jsonResult['balance'])
            scheduledAmount = str(jsonResult['scheduledAmount'])
            scheduledDate  = str(jsonResult['scheduledDate'])
            event['sessionAttributes']['balance'] = balance
            
    paymentInfoCache = PayInfo(accountNumber, scheduledDate, scheduledAmount, balance)
    return paymentInfoCache


#""" --- Intents --- """
def fulfill(event):
    slots = get_slots(event)
    intent_name = event['currentIntent']['name']
    
    if (intent_name == 'payment' and slots['paymentAmount'] != None):
        changeAccountValue(event)
        return close(event['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': 'Your payment of  $' + slots['paymentAmount'] + ' has been applied to your account. Your new balance is ' + event['sessionAttributes'].get('balance')})
    else:
        return close(event['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': 'Thanks for your call'})
                  
def obj_dict(obj):
    return obj.__dict__
    
def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': {
                'contentType': 'PlainText',
                'content': message
            }
        }
    }
    
def dispatch(event):
    print(json.dumps(event))
    """
    Called when the user specifies an intent for this bot.
    """

    #logger.debug('dispatch userId={}, intentName={}'.format(event['userId'], event['currentIntent']['name']))

    intent_name = event['currentIntent']['name']
    slots = get_slots(event)
    source = event['invocationSource']

    # Dispatch to your bot's intent handlers
    if intent_name == 'balance':
        payFo = getPaymentInfo(event)
        
        if (payFo!=None):
            event['sessionAttributes']['balance'] = '${}'.format(str(payFo.balance))
            
        if slots['makePayment'] == None:
            return delegate(event['sessionAttributes'], slots)
        else:
            if (slots['makePayment'] == 'yes'):
                return confirm_intent(event['sessionAttributes'], 'payment', None, 'Are you sure you would like to make a payment?')
            if (slots['makePayment'] == 'no'):
                return close(event['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': 'Thanks for your call, have a good day.'})
    
    # if intent_name == 'loans':
    #     loans = getLoans(event)
    #     print(loans)
    #     msg = 'Your loans are as follows: '
    #     for loan in loans:
    #         msg += 'Loan {} with a balance of ${}. '.format(loan['id'], loan['balance'])
    #     msg += 'Which loan would you like to manage?'
    #     event['sessionAttributes']['msg'] = msg
    #     return delegate(event['sessionAttributes'], slots) 
    #     #if (slots['loanID'] != None):
    #         #return elicit_slot(event['sessionAttributes'], 'loans', slots, 'loanID', msg)
        
    if intent_name == 'payment':
        payFo = getPaymentInfo(event)
        
        if (payFo!=None):
            event['sessionAttributes']['balance'] = str(payFo.balance)
            event['sessionAttributes']['scheduledAmount'] = str(payFo.amount)
            event['sessionAttributes']['scheduledDate'] = str(payFo.date)

        
        if (source == 'DialogCodeHook'):
            if (slots['paymentType'] == None):
                return delegate(event['sessionAttributes'], slots)
            if (slots['paymentConfirm'] == None):
                return delegate(event['sessionAttributes'], slots)
            
            #end call if customer decides not to continue
            if (slots['paymentConfirm'] == 'no'):
                return close(event['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': 'Thanks for your call, have a good day.'})
                
            if (slots['paymentAmount'] == None):
                return delegate(event['sessionAttributes'], slots)
            
            #input validation for paymentAmount
            if (float(slots['paymentAmount'])>float(payFo.balance)):
                return elicit_slot(event['sessionAttributes'], 
                                event['currentIntent']['name'],
                                slots,
                                "paymentAmount",
                                {'contentType': 'PlainText', 'content': 'your payment amount exceeds loan balance. Please chose a payment amount between 0 and {}'.format(payFo.balance)})
                                
                
                
            return delegate(event['sessionAttributes'], slots)
        elif (source == "FulfillmentCodeHook"):
            return fulfill(event)
        
    raise Exception('Intent with name ' + intent_name + ' not supported')
