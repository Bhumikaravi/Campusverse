// Usage: npm run set-role -- user@example.com admin
import mongoose from "mongoose";
import { env } from "../src/config/env.js";
import { User, ROLES } from "../src/models/User.js";

const [email, role] = process.argv.slice(2);
if (!email || !ROLES.includes(role)) {
  console.error(`Usage: npm run set-role -- <email> <${ROLES.join("|")}>`);
  process.exit(1);
}
await mongoose.connect(env.MONGODB_URI);
const user = await User.findOneAndUpdate({ email: email.toLowerCase() }, { role }, { new: true });
console.log(user ? `✔ ${user.email} is now ${user.role}` : "No user with that email (register first).");
await mongoose.disconnect();
