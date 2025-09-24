import { useState } from "react";
import { useAuthStore } from "../lib/authStore";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import { toast } from "sonner";

export function AuthCard() {
  const { login, register, isLoading } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (mode === "register") {
        await register({ username, password, full_name: fullName || undefined });
        toast.success("Registration successful");
      } else {
        await login({ username, password });
        toast.success("Login successful");
      }
    } catch (err: any) {
      toast.error(err?.message || "Action failed");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{mode === "register" ? "Create account" : "Sign in"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit}>
          {mode === "register" && (
            <Input
              placeholder="Full name (optional)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
            />
          )}
          <Input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
            required
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
          />
          <Button type="submit" disabled={isLoading}>
            {mode === "register" ? "Register" : "Login"}
          </Button>
          <Separator />
          <Button
            type="button"
            variant="secondary"
            onClick={() => setMode(mode === "register" ? "login" : "register")}
            disabled={isLoading}
          >
            {mode === "register" ? "Have an account? Sign in" : "Need an account? Register"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}


