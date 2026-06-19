import { FormEvent, KeyboardEvent, useState } from "react";
import { Send, Square } from "lucide-react";

interface ComposerProps {
  disabled?: boolean;
  streaming?: boolean;
  onSubmit: (value: string) => void;
}

export function Composer({ disabled, streaming, onSubmit }: ComposerProps) {
  const [value, setValue] = useState("");

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const question = value.trim();
    if (!question || disabled || streaming) return;
    setValue("");
    onSubmit(question);
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        disabled={disabled || streaming}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={keyDown}
        placeholder="Ask about the uploaded PDFs"
        rows={1}
        value={value}
      />
      <button className="send-button" disabled={disabled || streaming || !value.trim()} title={streaming ? "Streaming" : "Send"} type="submit">
        {streaming ? <Square size={17} /> : <Send size={17} />}
      </button>
    </form>
  );
}

