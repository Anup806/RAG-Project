import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

interface UploadDropzoneProps {
  disabled?: boolean;
  onUpload: (files: File[]) => void;
}

export function UploadDropzone({ disabled, onUpload }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function pickFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (files.length) onUpload(files);
    event.target.value = "";
  }

  function drop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files).filter(
      (file) => file.type === "application/pdf" || file.name.endsWith(".pdf")
    );
    if (files.length) onUpload(files);
  }

  return (
    <>
      <button
        className={`upload-zone ${dragging ? "is-dragging" : ""}`}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        title="Upload PDFs"
        type="button"
      >
        <UploadCloud size={20} />
        <span>Upload PDFs</span>
      </button>
      <input ref={inputRef} accept="application/pdf" multiple onChange={pickFiles} type="file" hidden />
    </>
  );
}

