from agents.state import QAState, ValidationResult


def validate_test_code(code: str) -> ValidationResult:
    """Check generated Python syntax without executing it."""
    if not code.strip():
        return {"valid": False, "message": "The model returned no test code."}

    try:
        compile(code, "test_generated.py", "exec", dont_inherit=True)
    except SyntaxError as error:
        location = f"Line {error.lineno}: " if error.lineno is not None else ""
        return {"valid": False, "message": f"{location}{error.msg}"}

    return {"valid": True, "message": "Python syntax is valid."}


def validate_generated_tests(state: QAState) -> dict[str, ValidationResult]:
    return {"validation_result": validate_test_code(state["test_cases"])}
