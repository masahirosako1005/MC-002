import type { Route } from "./daytrip-types";
import { LocalPhoto } from "./ui";
import { WoodcutArt } from "./WaArt";

export default function DaytripCover({
  route,
  priority,
}: {
  route: Route;
  priority: boolean;
}) {
  if (
    route.cover_id &&
    [
      "coffee",
      "coast",
      "woodland",
      "table",
      "pottery",
      "garden",
      "riverside",
    ].includes(route.cover_id)
  )
    return (
      <LocalPhoto
        src={`/api/covers/${route.cover_id}`}
        alt="過ごし方のイメージ写真"
        priority={priority}
      />
    );
  return <WoodcutArt priority={priority} />;
}
