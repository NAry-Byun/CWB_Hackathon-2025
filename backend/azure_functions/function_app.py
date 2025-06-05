# function_app.py - 강제 재배포용 최소 코드

import azure.functions as func
import json

app = func.FunctionApp()

@app.function_name(name="test")
@app.route(route="test")  
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "message": "run test function!",
            "status": "success",
            "method": req.method
        }),
        status_code=200,
        mimetype="application/json"
    )

@app.function_name(name="health")
@app.route(route="health")
def health_function(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "message": "Function App runs!",
            "timestamp": "2025-06-05"
        }),
        status_code=200,
        mimetype="application/json"
    )