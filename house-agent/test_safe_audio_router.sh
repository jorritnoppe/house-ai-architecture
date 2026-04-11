cd ~/house-agent
source venv/bin/activate

echo "=== living ==="
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"play some music in the living room"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"is living room music on"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"turn the living room music off"}' | python3 -m json.tool

echo "=== bathroom ==="
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"put music on in the bathroom"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"is bathroom music on"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"turn the bathroom music off"}' | python3 -m json.tool

echo "=== toilet ==="
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"play music in the toilet"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"is toilet music on"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"turn the toilet music off"}' | python3 -m json.tool

echo "=== party ==="
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"start the party music","confirmed":true}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"is party mode on"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/agent/query -H "Content-Type: application/json" -d '{"question":"stop the party music"}' | python3 -m json.tool
