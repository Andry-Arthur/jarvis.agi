"""CLI entry point — `python -m jarvis` or `jarvis` after `pip install -e .`

Usage:
  python -m jarvis            # Interactive voice loop
  python -m jarvis chat       # Text-only chat REPL
  python -m jarvis serve      # Start the FastAPI server
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()
console = Console()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("jarvis").setLevel(logging.INFO)


def _build_agent():
    from jarvis.core.agent import Agent
    from jarvis.core.memory import Memory
    from jarvis.core.scheduler import CancelReminderTool, ListRemindersTool, ReminderTool, TaskScheduler
    from jarvis.core.tools import ToolRegistry
    from jarvis.llm.router import LLMRouter

    router = LLMRouter.from_env()
    registry = ToolRegistry()

    from jarvis.integrations.discord_int import DiscordIntegration
    from jarvis.integrations.gmail import GmailIntegration
    from jarvis.integrations.instagram import InstagramIntegration
    from jarvis.integrations.youtube import YouTubeIntegration

    for integration in [
        GmailIntegration(),
        DiscordIntegration(),
        YouTubeIntegration(),
        InstagramIntegration(),
    ]:
        if integration.is_configured():
            registry.register_many(integration.get_tools())

    # Scheduler with audio reminder notification
    scheduler = TaskScheduler()
    scheduler.start()

    def _notify(msg: str):
        console.print(f"\n[bold yellow]⏰ REMINDER:[/bold yellow] {msg}")

    registry.register_many(
        [ReminderTool(scheduler, notify_callback=_notify), ListRemindersTool(scheduler), CancelReminderTool(scheduler)]
    )

    memory = Memory()
    return Agent(llm_router=router, tool_registry=registry, memory=memory)


# ── Voice loop ────────────────────────────────────────────────────────────────


async def voice_loop(agent) -> None:
    from jarvis.voice.stt import SpeechToText
    from jarvis.voice.tts import TextToSpeech
    from jarvis.voice.wake_word import WakeWordDetector

    wake_model = os.getenv("WAKE_WORD_MODEL", "")
    stt = SpeechToText(
        model_size=os.getenv("WHISPER_MODEL", "base"),
        device="cpu",
        compute_type="int8",
    )
    tts = TextToSpeech(voice=os.getenv("TTS_VOICE", "en-US-GuyNeural"))
    detector = WakeWordDetector(model_path=wake_model)

    # Pre-load Whisper now so first activation has no cold-start delay
    console.print("[dim]Loading speech recognition model…[/dim]")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, stt._load)

    console.print(
        Panel.fit(
            "[bold cyan]JARVIS.AGI[/bold cyan] — Voice Mode\n"
            "Say [bold]'Hey Jarvis'[/bold] to activate, [bold]Ctrl+C[/bold] to quit.",
            border_style="cyan",
        )
    )

    history: list[dict] = []

    async for _ in detector.listen_forever():
        console.print("[green]✓ Wake word detected![/green] Speak now…")
        await tts.speak("Yes?")

        text = await stt.record_and_transcribe()
        if not text.strip():
            await tts.speak("I didn't catch that. Please try again.")
            continue

        console.print(f"[bold]You:[/bold] {text}")

        console.print("[dim]Thinking…[/dim]")
        reply = await agent.run(text, history=history)

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        # Keep last 20 turns in context
        if len(history) > 40:
            history = history[-40:]

        console.print(Panel(Markdown(reply), title="[cyan]JARVIS[/cyan]", border_style="cyan"))
        await tts.speak(reply)
        console.print("[dim]Listening for wake word…[/dim]")


# ── Text chat REPL ────────────────────────────────────────────────────────────


async def chat_loop(agent) -> None:
    console.print(
        Panel.fit(
            "[bold cyan]JARVIS.AGI[/bold cyan] — Chat Mode\n"
            "Type your message and press Enter. Type [bold]exit[/bold] to quit.",
            border_style="cyan",
        )
    )

    history: list[dict] = []

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]You[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if user_input.lower() in ("exit", "quit", "bye"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if not user_input.strip():
            continue

        with console.status("[dim]Thinking…[/dim]"):
            reply = await agent.run(user_input, history=history)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 40:
            history = history[-40:]

        console.print(Panel(Markdown(reply), title="[cyan]JARVIS[/cyan]", border_style="cyan"))


# ── CLI commands ──────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """JARVIS.AGI — your free, self-hosted AI agent."""
    if ctx.invoked_subcommand is None:
        # Default: voice mode
        agent = _build_agent()
        try:
            asyncio.run(voice_loop(agent))
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/dim]")


@main.command()
def chat() -> None:
    """Start an interactive text chat session."""
    agent = _build_agent()
    try:
        asyncio.run(chat_loop(agent))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/dim]")


@main.command()
@click.option("--host", default=None, help="Bind host (overrides .env API_HOST)")
@click.option("--port", default=None, type=int, help="Bind port (overrides .env API_PORT)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode)")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Start the JARVIS.AGI API + WebSocket server."""
    import uvicorn

    _host = host or os.getenv("API_HOST", "0.0.0.0")
    _port = port or int(os.getenv("API_PORT", "8000"))

    console.print(
        Panel.fit(
            f"[bold cyan]JARVIS.AGI[/bold cyan] API\n"
            f"Listening on [bold]http://{_host}:{_port}[/bold]\n"
            f"WebSocket: [bold]ws://{_host}:{_port}/ws[/bold]",
            border_style="cyan",
        )
    )

    uvicorn.run(
        "jarvis.api.main:create_app",
        host=_host,
        port=_port,
        reload=reload,
        factory=True,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
