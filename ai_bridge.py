import sys
import json
from llama_cpp import Llama

try:
    llm = Llama(
        model_path=r"C:\\Users\\JAY ABI ADHI\\Desktop\\IDE\\TTC Mechanism\\deepseek-coder\\deepseek-coder-1.3b-instruct.Q3_K_M.gguf",
        lib_path=r"C:\\Users\\JAY ABI ADHI\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\llama_cpp\\lib\\llama.dll",
        verbose=False,
        n_threads=8,
        n_ctx=16384
    )

    conversation = sys.argv[1] if len(sys.argv) > 1 else "Write a quick sort algorithm in Python."

    persona = (
        "You are Vel Code, an AI programming assistant developed by Abinesh Kumar. "
        "Greet users as 'Vel Code'. Be friendly, enthusiastic, and highly skilled. "
        "Provide complete, well-structured code with explanations and comments. "
        "Maintain a positive, supportive attitude."
    )

    full_prompt = (
        f"### System:\n{persona}\n"
        f"### Instruction:\n{persona}\n{conversation}\n"
        "### Response:\n"
    )

    resp = llm(
        full_prompt,
        max_tokens=1000,
        temperature=0.35,
        stop=["<|EOT|>", "### Instruction:"]
    )

    reply = resp["choices"][0]["text"].strip()
    if not any(g in reply.lower() for g in ["vel code", "hello", "hi"]):
        reply = f"Hello! I'm Vel Code, your friendly AI coding assistant! {reply}"

    print(json.dumps({"reply": reply, "ok": True}))
except Exception as e:
    print(json.dumps({"reply": str(e), "ok": False}))
