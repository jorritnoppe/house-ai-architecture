TOOL_SPEC = {
  "name": "AI_gen_valid_test_tool",
  "description": "Validation test tool.",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "safety": "read_only"
}

def run(args):
  return {"ok": True, "answer": "valid test ok", "data": {"stage": "test"}}