import asyncio
from backend.core.model_availability import (
    model_availability,
    NoModelsAvailableError,
    OllamaOfflineError
)
from backend.core.model_fallback import FALLBACK_MODELS
from backend.core.router import router, resolve_model

def test_fallback_selection():
    """Verify fallback selection prioritizes candidates correctly."""
    model_availability.installed_models = {"qwen2.5-coder:7b"}
    selected = model_availability.select_available([
        "llama3.1:8b",
        "qwen2.5-coder:7b"
    ])
    assert selected == "qwen2.5-coder:7b", f"Expected qwen2.5-coder:7b, got {selected}"
    print("✓ Test 1 Passed: Fallback selection priority works.")

async def test_greeting_scenarios():
    """Verify greeting routing under different availability conditions."""
    # Scenario A: Llama installed -> Use Llama for greetings
    model_availability.is_online = True
    model_availability.installed_models = {"llama3.1:8b", "qwen2.5-coder:7b"}
    decision = await router.route("hello", simulate=False)
    assert decision.recommended_models == ["llama3.1:8b"]
    assert len(decision.plan.stages) == 1
    assert decision.plan.stages[0].model_id == "llama3.1:8b"
    print("✓ Test 2A Passed: Greeting uses Llama when installed.")

    # Scenario B: Llama missing, Qwen installed -> Use Qwen for greetings
    model_availability.installed_models = {"qwen2.5-coder:7b"}
    decision = await router.route("hello", simulate=False)
    assert decision.recommended_models == ["qwen2.5-coder:7b"]
    assert len(decision.plan.stages) == 1
    assert decision.plan.stages[0].model_id == "qwen2.5-coder:7b"
    print("✓ Test 2B Passed: Greeting falls back to Qwen when Llama is missing.")

    # Scenario C: Multilingual Hindi / Hinglish greetings
    model_availability.installed_models = {"llama3.2:1b"}
    decision_hi = await router.route("Namaste bhai, kaise ho?", simulate=False)
    assert decision_hi.task_type == "general" and decision_hi.sub_domain == "greeting"
    assert decision_hi.recommended_models == ["llama3.2:1b"]

    decision_hinglish = await router.route("kyaaa bhsi", simulate=False)
    assert decision_hinglish.task_type == "general" and decision_hinglish.sub_domain == "greeting"
    assert decision_hinglish.recommended_models == ["llama3.2:1b"]
    print("✓ Test 2C Passed: Multilingual Hindi & Hinglish ('kyaaa bhsi', 'Namaste') recognized and routed to llama3.2:1b.")

async def test_collaboration_scenarios():
    """Verify collaboration preservation rules for complex tasks."""
    model_availability.is_online = True
    
    # Complex task with 1 installed model -> Single Model Response
    model_availability.installed_models = {"qwen2.5-coder:7b"}
    complex_prompt = "Build a complete system for production distributed transactions with two-phase commit step by step in Python"
    decision = await router.route(complex_prompt, simulate=False)
    assert decision.recommended_models == ["qwen2.5-coder:7b"]
    assert len(decision.plan.stages) == 1, f"Expected 1 stage, got {len(decision.plan.stages)}"
    assert decision.plan.stages[0].model_id == "qwen2.5-coder:7b"
    assert decision.plan.synthesis_required is False
    print("✓ Test 3A Passed: Complex task with 1 model consolidates to Single Model Response.")

    # Complex task with 2 installed models -> Two-model collaboration
    model_availability.installed_models = {"qwen2.5-coder:7b", "llama3.1:8b"}
    decision = await router.route(complex_prompt, simulate=False)
    assert len(decision.plan.stages) == 2, f"Expected 2 stages, got {len(decision.plan.stages)}"
    assert decision.recommended_models == ["qwen2.5-coder:7b", "llama3.1:8b"]
    assert decision.plan.synthesis_required is True
    print("✓ Test 3B Passed: Complex task with 2 models plans Two-Model collaboration.")

    # Complex task with 3 installed models -> Full 3-model collaboration
    model_availability.installed_models = {"qwen2.5-coder:7b", "deepseek-r1:7b", "llama3.1:8b"}
    decision = await router.route(complex_prompt, simulate=False)
    assert len(decision.plan.stages) == 3, f"Expected 3 stages, got {len(decision.plan.stages)}"
    assert decision.recommended_models == ["qwen2.5-coder:7b", "deepseek-r1:7b", "llama3.1:8b"]
    assert decision.plan.synthesis_required is True
    print("✓ Test 3C Passed: Complex task with 3 models plans Full 3-Stage collaboration.")

    # Simple non-greeting task with 3 installed models -> Uses only 1 model (Direct Answer)
    simple_prompt = "What is 2 + 2?"
    decision = await router.route(simple_prompt, simulate=False)
    assert len(decision.plan.stages) == 1, f"Expected 1 stage for simple task, got {len(decision.plan.stages)}"
    assert decision.plan.synthesis_required is False
    print("✓ Test 3D Passed: Simple prompt with 3 installed models uses only 1 model.")

async def test_no_models_installed():
    """Verify explicit NoModelsAvailableError when no models are installed."""
    model_availability.is_online = True
    model_availability.installed_models = set()
    
    try:
        await router.route("hello", simulate=False)
        assert False, "Should have raised NoModelsAvailableError"
    except NoModelsAvailableError as e:
        assert "no compatible AI models are installed" in e.message
        assert len(e.suggested_install) > 0
        print("✓ Test 4 Passed: Empty model pool raises NoModelsAvailableError.")

async def test_ollama_offline():
    """Verify explicit OllamaOfflineError when Ollama daemon is offline."""
    model_availability.is_online = False
    model_availability.installed_models = set()
    model_availability.last_error = "Could not connect to Ollama at http://127.0.0.1:11434. Ensure Ollama is running ('ollama serve')."
    
    try:
        await router.route("hello", simulate=False)
        assert False, "Should have raised OllamaOfflineError"
    except OllamaOfflineError as e:
        assert "Could not connect to Ollama" in e.message
        print("✓ Test 5 Passed: Offline Ollama raises OllamaOfflineError.")

async def run_all():
    print("--- Running SYNORA v0.4.2 Acceptance Unit Tests ---")
    model_availability._mock_mode = True
    test_fallback_selection()
    await test_greeting_scenarios()
    await test_collaboration_scenarios()
    await test_no_models_installed()
    await test_ollama_offline()
    print("--- ALL 5 ACCEPTANCE TESTS PASSED! ---")

if __name__ == "__main__":
    asyncio.run(run_all())
