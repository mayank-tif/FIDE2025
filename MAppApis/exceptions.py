from rest_framework.views import exception_handler
from rest_framework import serializers  # Add this import

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(response.data, dict):
            # Flatten ValidationError into {"error": {"message": "..."}}
            if "non_field_errors" in response.data:
                message = response.data["non_field_errors"][0]
            elif "detail" in response.data:
                message = response.data["detail"]
            else:
                # Get first field error message
                first_key = list(response.data.keys())[0]
                message = response.data[first_key]
                if isinstance(message, list):
                    message = message[0]

            response.data = {"error": {"message": str(message)}}

    return response
