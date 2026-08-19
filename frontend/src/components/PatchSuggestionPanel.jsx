const PATCH_TYPE_LABEL = {
  system_prompt: "System Prompt",
  input_validation: "Input Validation",
  permission_scope: "Permission Scope",
  code: "Code Fix",
};

export default function PatchSuggestionPanel({ patch }) {
  const copy = () => navigator.clipboard.writeText(patch.patch_content);

  return (
    <div className="mt-3 rounded-lg border border-cyan/30 bg-cyan-dim/60 p-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-cyan">
          {PATCH_TYPE_LABEL[patch.patch_type] || patch.patch_type}
        </span>
        <button
          onClick={copy}
          className="font-mono text-[11px] text-text-muted hover:text-cyan"
        >
          Copy
        </button>
      </div>
      <p className="mt-1.5 text-sm font-medium text-text-primary">{patch.summary}</p>
      <p className="mt-1 text-xs text-text-muted">{patch.explanation}</p>
      <pre className="mt-2 overflow-x-auto rounded border border-grid bg-panel p-2.5 font-mono text-[11px] text-text-primary">
        {patch.patch_content}
      </pre>
    </div>
  );
}
