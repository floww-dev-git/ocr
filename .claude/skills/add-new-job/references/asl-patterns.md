# ASL (Amazon States Language) Patterns

Common patterns for Step Function state machine definitions used with `BaseWorkflow` jobs.

## File Convention

ASL definitions live in `<app>/workflows/<workflow_name>/state_machine.py`. The module exports a single function:

```python
from step_functions.config import StepFunctionConfig

STEP_FUNCTION_TYPE = "<app>.<action>"  # Must match workflow's job_type

def get_<workflow_name>_json(config: StepFunctionConfig) -> dict:
    lambda_arn = config.lambda_function_arn
    return { ... }  # ASL dict
```

The workflow class imports this function in `get_state_machine_definition()`.

## Required Task State Parameters

Every Task state that invokes a workflow operation MUST include these fields in `Parameters`:

```python
"Parameters": {
    "operation": "<operation_name>",          # Matches @operation(name="...") on the workflow class
    "stepFunctionType": STEP_FUNCTION_TYPE,   # Matches workflow's job_type — routing key for step_function_handler
    "isJobsEngineWorkflow": True,             # Discriminant flag for the handler
    "job_id.$": "$.job_id",                   # Always pass job_id through
    # ... additional workflow-specific fields using JSON Path (.$) syntax
},
```

Without `stepFunctionType` and `operation`, the `step_function_handler` cannot route the Lambda event to the correct workflow and operation method.

## Standard Retry Policy

Use for all Task states. Handles AWS transient errors with exponential backoff:

```python
RETRY_POLICY = [
    {
        "ErrorEquals": [
            "ServiceUnavailable",
            "ThrottlingException",
        ],
        "IntervalSeconds": 2,
        "MaxAttempts": 5,
        "BackoffRate": 1.5,
    }
]
```

Apply to each Task state:
```python
"Retry": RETRY_POLICY,
```

## Standard Catch-All Pattern

Every Task state should catch unhandled errors and route to a global error handler:

```python
"Catch": [
    {
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "HandleError",
    }
],
```

## Terminal States

Every state machine needs exactly two terminal states:

```python
"Success": {
    "Type": "Succeed",
    "Comment": "<Workflow name> completed successfully",
},
"Failed": {
    "Type": "Fail",
    "Error": "<WorkflowName>Failed",
    "Cause": "<Workflow name> failed due to an unrecoverable error",
},
```

## Pattern 1: Linear Pipeline

Init -> Process -> Finalize, with a global error handler.

```python
def get_linear_workflow_json(config: StepFunctionConfig) -> dict:
    lambda_arn = config.lambda_function_arn

    return {
        "Comment": "Description of what this workflow does",
        "StartAt": "InitJob",
        "TimeoutSeconds": config.timeout_seconds,
        "States": {
            "InitJob": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "init_job",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "execution_arn.$": "$$.Execution.Id",
                    "payload.$": "$.payload",
                },
                "ResultPath": "$.init_result",
                "Retry": RETRY_POLICY,
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "Process",
            },
            "Process": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "process",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "init_result.$": "$.init_result",
                },
                "ResultPath": "$.process_result",
                "Retry": RETRY_POLICY,
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "Finalize",
            },
            "Finalize": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "finalize",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                },
                "ResultPath": "$.finalize_result",
                "Retry": RETRY_POLICY,
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "Success",
            },
            "HandleError": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "handle_error",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "error.$": "$.error",
                },
                "ResultPath": "$.error_result",
                "Next": "Failed",
            },
            "Success": {
                "Type": "Succeed",
                "Comment": "Workflow completed successfully",
            },
            "Failed": {
                "Type": "Fail",
                "Error": "WorkflowFailed",
                "Cause": "Workflow failed due to an unrecoverable error",
            },
        },
    }
```

## Pattern 2: Parallel Batch Processing

Init -> Map (parallel batches with per-batch error handling) -> Finalize. This is the pattern used by `ManualAwTriggerWorkflow`.

```python
BATCH_PROCESSOR_MAX_CONCURRENCY = 5

def get_parallel_batch_workflow_json(config: StepFunctionConfig) -> dict:
    lambda_arn = config.lambda_function_arn

    return {
        "Comment": "Parallel batch processing workflow",
        "StartAt": "InitJob",
        "TimeoutSeconds": config.timeout_seconds,
        "States": {
            "InitJob": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "init_job",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "execution_arn.$": "$$.Execution.Id",
                    "payload.$": "$.payload",
                },
                "ResultPath": "$.init_result",
                "Retry": RETRY_POLICY,
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "ProcessBatches",
            },
            "ProcessBatches": {
                "Type": "Map",
                "InputPath": "$.init_result",
                "ItemsPath": "$.batch_keys",         # init_job returns {"job_id": ..., "batch_keys": [...]}
                "Parameters": {
                    "job_id.$": "$.job_id",
                    "batch_key.$": "$$.Map.Item.Value",
                },
                "MaxConcurrency": BATCH_PROCESSOR_MAX_CONCURRENCY,
                "ResultPath": "$.batch_results",
                "Iterator": {
                    "StartAt": "ProcessBatch",
                    "States": {
                        "ProcessBatch": {
                            "Type": "Task",
                            "Resource": lambda_arn,
                            "Parameters": {
                                "operation": "process_batch",
                                "stepFunctionType": STEP_FUNCTION_TYPE,
                                "isJobsEngineWorkflow": True,
                                "job_id.$": "$.job_id",
                                "batch_key.$": "$.batch_key",
                            },
                            "ResultPath": "$.process_result",
                            "Retry": RETRY_POLICY,
                            "Catch": [
                                {
                                    "ErrorEquals": ["States.ALL"],
                                    "ResultPath": "$.error",
                                    "Next": "RecordBatchFailure",
                                }
                            ],
                            "End": True,
                        },
                        "RecordBatchFailure": {
                            "Type": "Task",
                            "Resource": lambda_arn,
                            "Parameters": {
                                "operation": "record_batch_failure",
                                "stepFunctionType": STEP_FUNCTION_TYPE,
                                "isJobsEngineWorkflow": True,
                                "job_id.$": "$.job_id",
                                "batch_key.$": "$.batch_key",
                                "error.$": "$.error",
                            },
                            "ResultPath": "$.failure_result",
                            "Retry": RETRY_POLICY,
                            "End": True,
                        },
                    },
                },
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "Finalize",
            },
            "Finalize": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "finalize",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "batch_keys.$": "$.init_result.batch_keys",
                },
                "ResultPath": "$.finalize_result",
                "Retry": RETRY_POLICY,
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleError",
                    }
                ],
                "Next": "Success",
            },
            "HandleError": {
                "Type": "Task",
                "Resource": lambda_arn,
                "Parameters": {
                    "operation": "handle_error",
                    "stepFunctionType": STEP_FUNCTION_TYPE,
                    "isJobsEngineWorkflow": True,
                    "job_id.$": "$.job_id",
                    "error.$": "$.error",
                },
                "ResultPath": "$.error_result",
                "Next": "Failed",
            },
            "Success": {
                "Type": "Succeed",
                "Comment": "Workflow completed successfully",
            },
            "Failed": {
                "Type": "Fail",
                "Error": "WorkflowFailed",
                "Cause": "Workflow failed due to an unrecoverable error",
            },
        },
    }
```

## JSON Path Quick Reference

| Syntax | Meaning |
|--------|---------|
| `"field.$": "$.job_id"` | Pass `job_id` from current state input |
| `"field.$": "$$.Execution.Id"` | Pass the Step Functions execution ARN (context object) |
| `"field.$": "$$.Map.Item.Value"` | Current item in a Map iterator |
| `"InputPath": "$.init_result"` | Use `init_result` from state input as this state's input |
| `"ResultPath": "$.my_result"` | Store this state's output under `my_result` key |
| `"ItemsPath": "$.batch_keys"` | Iterate over `batch_keys` array in Map state |

## State Data Size Limit

Step Functions state data (`$`) has a **256KB limit**. Bulk data (CSV rows, large payloads) must flow through S3, not through `$`. The `init_job` operation should upload batch data to S3 and pass only S3 keys through the state machine.

## Canonical Example

`automation_workflows/workflows/manual_aw_trigger/state_machine.py` — parallel batch processing pattern with 5 concurrent batch processors, per-batch error recording, and a global error handler.
