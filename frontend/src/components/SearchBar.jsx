import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";

export default function SearchBar({
  value,
  onChange,
  placeholder = "Search materials, subjects, departments...",
  className = "",
  onSubmit,
}) {
  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState(value || "");

  useEffect(() => {
    if (isControlled) {
      setInternalValue(value || "");
    }
  }, [value, isControlled]);

  const handleChange = (e) => {
    const val = e.target.value;
    if (!isControlled) {
      setInternalValue(val);
    }
    onChange?.(val);
  };

  const handleClear = () => {
    if (!isControlled) {
      setInternalValue("");
    }
    onChange?.("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const current = isControlled ? value : internalValue;
    if (onSubmit) {
      onSubmit(current);
    } else {
      onChange?.(current);
    }
  };

  const currentDisplay = isControlled ? value : internalValue;

  return (
    <form
      onSubmit={handleSubmit}
      className={`relative flex w-full items-center ${className}`}
      role="search"
    >
      <div className="pointer-events-none absolute left-3.5 flex items-center text-gray-400">
        <Search size={18} />
      </div>

      <input
        type="text"
        value={currentDisplay || ""}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full rounded-xl border border-gray-300 bg-white py-3 pl-10 pr-10 text-sm text-gray-900 shadow-sm transition placeholder:text-gray-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-brand-500 dark:focus:ring-brand-950"
      />

      {currentDisplay && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-3 rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200"
          aria-label="Clear search"
        >
          <X size={15} />
        </button>
      )}
    </form>
  );
}