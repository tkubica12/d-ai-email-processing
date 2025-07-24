import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()


@app.service_bus_topic_trigger(arg_name="azservicebus", subscription_name="submission-intake-functions", topic_name="new-submissions",
                               connection="ServiceBusConnection") 
def submission_analyzer(azservicebus: func.ServiceBusMessage):
    logging.info('Python ServiceBus Topic trigger processed a message: %s',
                azservicebus.get_body().decode('utf-8'))
