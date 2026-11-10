import { useId, useState } from "react";
import Choice from "./Choice";
import "./residence.css";

export type ResidenceArea = {
  id: string;
  prefecture: string;
  city: string;
  label: string;
  latitude: number;
  longitude: number;
};
export type ResidenceDestination = {
  id: string;
  name: string;
  prefecture: string;
  latitude: number;
  longitude: number;
  fictional: boolean;
};
export type ResidenceCatalog = {
  items: ResidenceArea[];
  destination: ResidenceDestination;
  precision: "municipality_representative";
};
export type Residence = {
  area: ResidenceArea | null;
  share_area_analytics: boolean;
  version: number;
  updated_at: string | null;
};

export default function ResidenceFields({
  areas,
  areaId,
  onAreaChange,
  shared,
  onSharedChange,
  disabled = false,
  allowUnset = false,
  onIncompleteChange,
}: {
  areas: ResidenceArea[];
  areaId: string;
  onAreaChange: (id: string) => void;
  shared: boolean;
  onSharedChange: (value: boolean) => void;
  disabled?: boolean;
  allowUnset?: boolean;
  onIncompleteChange?: (value: boolean) => void;
}) {
  const id = useId();
  const [prefecture, setPrefecture] = useState(
    () => areas.find((area) => area.id === areaId)?.prefecture || "",
  );
  const prefectures = [...new Set(areas.map((area) => area.prefecture))];
  return (
    <fieldset className="residence-fields" disabled={disabled}>
      <legend>お住まいの地域</legend>
      <p className="residence-note">
        市区町村まで。番地は不要で、プロフィールには公開しません。
      </p>
      <div className="residence-area-row">
        <label className="field" htmlFor={`${id}-prefecture`}>
          都道府県
          <Choice
            id={`${id}-prefecture`}
            value={prefecture}
            disabled={disabled}
            onChange={(event) => {
              setPrefecture(event.target.value);
              onAreaChange("");
              onSharedChange(false);
              onIncompleteChange?.(true);
            }}
          >
            <option value="">都道府県を選ぶ</option>
            {prefectures.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Choice>
        </label>
        <label className="field" htmlFor={`${id}-city`}>
          市区町村
          <Choice
            id={`${id}-city`}
            value={areaId}
            disabled={disabled || !prefecture}
            onChange={(event) => {
              onAreaChange(event.target.value);
              onIncompleteChange?.(!event.target.value);
            }}
          >
            <option value="">市区町村を選ぶ</option>
            {areas
              .filter((area) => area.prefecture === prefecture)
              .map((area) => (
                <option key={area.id} value={area.id}>
                  {area.city}
                </option>
              ))}
          </Choice>
        </label>
      </div>
      {allowUnset && (
        <button
          className="text-button"
          type="button"
          disabled={disabled || (!areaId && !prefecture)}
          onClick={() => {
            setPrefecture("");
            onAreaChange("");
            onSharedChange(false);
            onIncompleteChange?.(false);
          }}
        >
          地域を未設定にする
        </button>
      )}
      <label className="residence-sharing">
        <input
          type="checkbox"
          checked={shared}
          disabled={disabled || !areaId}
          onChange={(event) => onSharedChange(event.target.checked)}
        />
        <span>
          居住地域を事業者の地域別集計に含める
          <small>
            任意。個人の住所は渡さず、少人数の地域は表示しません。あとから変更できます。
          </small>
        </span>
      </label>
    </fieldset>
  );
}
