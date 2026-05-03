import pino from "pino";

const isProduction = process.env.NODE_ENV === "production";
const isBrowser = typeof window !== "undefined";

export const logger = pino({
    level: process.env.LOG_LEVEL || (isProduction ? "info" : "debug"),
    ...(isBrowser ? {
        browser: {
            asObject: true
        }
    } : {
        transport: isProduction
            ? undefined
            : {
                  target: "pino-pretty",
                  options: {
                      colorize: true,
                      ignore: "pid,hostname",
                      translateTime: "SYS:standard",
                  },
              }
    })
});
