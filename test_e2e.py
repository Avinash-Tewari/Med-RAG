"""End-to-end test for the Medical RAG Platform."""
import json
import urllib.request
import urllib.error
import time

BASE = "http://127.0.0.1:8000"

def test_api():
    print("=" * 60)
    print("MedAdvisor — End-to-End Test")
    print("=" * 60)

    # 1. Check documents endpoint
    print("\n[1] GET /api/documents ...")
    r = urllib.request.urlopen(f"{BASE}/api/documents")
    print(f"    Status: {r.status}")
    data = json.loads(r.read())
    print(f"    Documents: {len(data['documents'])}")

    # 2. Upload sample medical document
    print("\n[2] POST /api/upload (test_sample.txt) ...")
    with open("test_sample.txt", "rb") as f:
        file_data = f.read()
    
    boundary = "----TestBoundary123"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test_sample.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BASE}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    result = json.loads(r.read())
    print(f"    Status: {r.status}")
    print(f"    Result: {json.dumps(result, indent=2)}")

    # 3. Check documents list now has 1 doc
    print("\n[3] GET /api/documents (should have 1 doc) ...")
    r = urllib.request.urlopen(f"{BASE}/api/documents")
    data = json.loads(r.read())
    print(f"    Documents: {len(data['documents'])}")
    for doc in data["documents"]:
        print(f"    - {doc['filename']} ({doc['chunk_count']} chunks)")

    # 4. Query — grounded question (should find answer)
    print("\n[4] POST /api/query — Grounded question ...")
    print('    Q: "What is the first-line treatment for Type 2 Diabetes?"')
    query_data = json.dumps({"question": "What is the first-line treatment for Type 2 Diabetes?"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/query",
        data=query_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    answer = json.loads(r.read())
    print(f"    has_answer: {answer.get('has_answer')}")
    print(f"    confidence: {answer.get('confidence')}")
    print(f"    reasoning_steps: {len(answer.get('reasoning_steps', []))}")
    print(f"    citations: {len(answer.get('citations', []))}")
    print(f"    answer: {answer.get('answer', '')[:200]}...")

    # 5. Query — out-of-scope question (should refuse)
    print("\n[5] POST /api/query — Out-of-scope question ...")
    print('    Q: "What is the best treatment for brain cancer?"')
    query_data = json.dumps({"question": "What is the best treatment for brain cancer?"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/query",
        data=query_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    answer = json.loads(r.read())
    print(f"    has_answer: {answer.get('has_answer')}")
    print(f"    confidence: {answer.get('confidence')}")
    print(f"    answer: {answer.get('answer', '')[:200]}...")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    test_api()
