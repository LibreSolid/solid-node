export interface MeshDictionary {
    [path: string]: THREE.Mesh;
}

// The "Raw" operations come as strings and have to be evaluated to numbers
type RotationRawOperation = [
  "r", string, [number, number, number]
];

type TranslationRawOperation = [
  "t", [string, string, string]
];

export type RawOperation = RotationRawOperation | TranslationRawOperation;

export type RotationOperation = [
  "r", number, [number, number, number]
];

export type TranslationOperation = [
  "t", [number, number, number]
];

export type Operation = RotationOperation | TranslationOperation;

export interface OperationDictionary {

  [path: string]: Operation[];
}
