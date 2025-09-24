import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { useAuthStore } from "../lib/authStore";

export function Home() {
  const { user, logout } = useAuthStore();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Welcome{user?.full_name ? `, ${user.full_name}` : ""}</CardTitle>
      </CardHeader>
      <CardContent>
              <Button onClick={logout}>Logout</Button>
      </CardContent>
    </Card>
  );
}


