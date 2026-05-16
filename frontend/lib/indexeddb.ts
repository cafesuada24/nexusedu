import { openDB, type IDBPDatabase } from "idb";

const DB_NAME = "NexusEduCSVStore";
const STORE_NAME = "uploadState";
const DB_VERSION = 1;

interface CSVStoreSchema {
    uploadState: {
        key: string;
        value: any;
    };
}

let dbPromise: Promise<IDBPDatabase<CSVStoreSchema>> | null = null;

function getDB() {
    if (typeof window === "undefined") return null;
    if (!dbPromise) {
        dbPromise = openDB<CSVStoreSchema>(DB_NAME, DB_VERSION, {
            upgrade(db) {
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME);
                }
            },
        });
    }
    return dbPromise;
}

export async function setPersistentState(key: string, value: any) {
    const db = await getDB();
    if (!db) return;
    await db.put(STORE_NAME, value, key);
}

export async function getPersistentState<T>(key: string): Promise<T | null> {
    const db = await getDB();
    if (!db) return null;
    return (await db.get(STORE_NAME, key)) as T;
}

export async function clearPersistentState(key: string) {
    const db = await getDB();
    if (!db) return;
    await db.delete(STORE_NAME, key);
}

export async function clearAllPersistentState() {
    const db = await getDB();
    if (!db) return;
    await db.clear(STORE_NAME);
}
