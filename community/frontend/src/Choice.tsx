import {
  Children,
  isValidElement,
  useEffect,
  useLayoutEffect,
  useId,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { Icon } from "./ui";
type Option = { value: string; label: ReactNode };
export default function Choice({
  value,
  onChange,
  children,
  disabled = false,
  id,
}: {
  value: string | number;
  onChange: (event: { target: { value: string } }) => void;
  children: ReactNode;
  disabled?: boolean;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const [labelText, setLabelText] = useState("");
  const generated = useId();
  const listId = `choice-${generated}`;
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const root = useRef<HTMLSpanElement>(null);
  const options: Option[] = Children.toArray(children)
    .filter(isValidElement)
    .map((child) => {
      const props = child.props as {
        value: string | number;
        children: ReactNode;
      };
      return { value: String(props.value), label: props.children };
    });
  const selected = options.find((o) => o.value === String(value));
  useLayoutEffect(() => {
    const label = root.current?.closest("label");
    if (!label) return;
    const text = Array.from(label.childNodes)
      .filter((node) => node.nodeType === Node.TEXT_NODE)
      .map((node) => node.textContent || "")
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    setLabelText(text);
  }, []);
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    const frame = requestAnimationFrame(() => {
      const buttons =
        menu.current?.querySelectorAll<HTMLButtonElement>("[role=option]");
      const index = Math.max(
        0,
        options.findIndex((o) => o.value === String(value)),
      );
      buttons?.[index]?.focus();
    });
    return () => {
      document.removeEventListener("pointerdown", outside);
      cancelAnimationFrame(frame);
    };
  }, [open]);
  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);
  return (
    <span ref={root} className="choice-field">
      <button
        type="button"
        id={id}
        ref={trigger}
        className="choice-trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={labelText || undefined}
        aria-describedby={labelText ? `${listId}-value` : undefined}
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            setOpen(true);
          }
        }}
      >
        <span id={`${listId}-value`}>
          {selected?.label || "選んでください"}
        </span>
        <Icon name="arrow" />
      </button>
      <div
        ref={menu}
        id={listId}
        className="choice-menu"
        role="listbox"
        aria-label={labelText ? `${labelText}の選択肢` : "選択肢"}
        hidden={!open}
        onKeyDown={(e) => {
          const items = Array.from(
            menu.current?.querySelectorAll<HTMLButtonElement>(
              "[role=option]",
            ) || [],
          );
          const index = items.indexOf(
            document.activeElement as HTMLButtonElement,
          );
          let next = index;
          if (e.key === "ArrowDown") next = (index + 1) % items.length;
          else if (e.key === "ArrowUp")
            next = (index - 1 + items.length) % items.length;
          else if (e.key === "Home") next = 0;
          else if (e.key === "End") next = items.length - 1;
          else if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            setOpen(false);
            trigger.current?.focus();
            return;
          } else if (e.key === "Tab") {
            setOpen(false);
            return;
          } else return;
          e.preventDefault();
          items[next]?.focus();
        }}
      >
        {options.map((o) => (
          <button
            type="button"
            className="choice-option"
            role="option"
            aria-selected={String(value) === o.value}
            key={o.value}
            tabIndex={-1}
            onClick={() => {
              onChange({ target: { value: o.value } });
              setOpen(false);
              trigger.current?.focus();
            }}
          >
            {o.label}
            {String(value) === o.value && <Icon name="check" />}
          </button>
        ))}
      </div>
    </span>
  );
}
