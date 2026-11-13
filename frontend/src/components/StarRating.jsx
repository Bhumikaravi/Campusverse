import { useState } from "react";
import { Star } from "lucide-react";

export function StarDisplay({ rating = 0, count, size = 14 }) {
  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            size={size}
            className={i <= Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-gray-300 dark:text-gray-700"}
          />
        ))}
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">
        {rating.toFixed(1)} {count != null && `(${count})`}
      </span>
    </div>
  );
}

export function StarInput({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(i)}
        >
          <Star
            size={24}
            className={
              i <= (hover || value)
                ? "fill-amber-400 text-amber-400"
                : "text-gray-300 dark:text-gray-700"
            }
          />
        </button>
      ))}
    </div>
  );
}
