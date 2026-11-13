import { Link } from "react-router-dom";
import { BookOpen, Github, Twitter, Linkedin } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-black/20 bg-[#3e362e] text-white/80">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-4 py-12 sm:px-6 md:grid-cols-4">
        <div className="col-span-2 md:col-span-1">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#93785b] text-white shadow-sm">
              <BookOpen size={17} />
            </div>
            <span className="font-display text-lg font-bold text-white">CampusVerse</span>
          </div>
          <p className="text-sm text-white/70">
            Learn. Share. Grow together — a modern home for student study materials.
          </p>
          <div className="mt-4 flex gap-3 text-white/60">
            <a href="#" aria-label="Github" className="hover:text-white transition"><Github size={18} /></a>
            <a href="#" aria-label="Twitter" className="hover:text-white transition"><Twitter size={18} /></a>
            <a href="#" aria-label="LinkedIn" className="hover:text-white transition"><Linkedin size={18} /></a>
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-white">Browse</h4>
          <ul className="space-y-2 text-sm text-white/70">
            <li><Link to="/categories" className="hover:text-white transition">Categories</Link></li>
            <li><Link to="/upload" className="hover:text-white transition">Upload notes</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-white">Account</h4>
          <ul className="space-y-2 text-sm text-white/70">
            <li><Link to="/login" className="hover:text-white transition">Log in</Link></li>
            <li><Link to="/register" className="hover:text-white transition">Sign up</Link></li>
            <li><Link to="/upload" className="hover:text-white transition">Upload material</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-white">Legal</h4>
          <ul className="space-y-2 text-sm text-white/70">
            <li><a href="#" className="hover:text-white transition">Privacy policy</a></li>
            <li><a href="#" className="hover:text-white transition">Terms of use</a></li>
            <li><a href="#" className="hover:text-white transition">Contact</a></li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10 py-4 text-center text-xs text-white/50">
        © {new Date().getFullYear()} CampusVerse. Built by students, for students.
      </div>
    </footer>
  );
}
