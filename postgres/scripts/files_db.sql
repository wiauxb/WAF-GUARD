-- Adminer 4.17.1 PostgreSQL 17.4 (Debian 17.4-1.pgdg120+2) dump

DROP TABLE IF EXISTS "analysis_tasks";
CREATE TABLE "public"."analysis_tasks" (
    "config_id" integer NOT NULL,
    "status" text NOT NULL,
    "progress" integer NOT NULL,
    "id" text NOT NULL,
    CONSTRAINT "parsing_tasks_id" UNIQUE ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "configs";
DROP SEQUENCE IF EXISTS configs_id_seq;
CREATE SEQUENCE configs_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 21 CACHE 1;

CREATE TABLE "public"."configs" (
    "id" integer DEFAULT nextval('configs_id_seq') NOT NULL,
    "nickname" text NOT NULL,
    "parsed" boolean DEFAULT false NOT NULL,
    "loaded_at" date DEFAULT CURRENT_DATE NOT NULL,
    CONSTRAINT "configs_id" UNIQUE ("id"),
    CONSTRAINT "configs_nickname" UNIQUE ("nickname")
) WITH (oids = false);


DROP TABLE IF EXISTS "dumps";
CREATE TABLE "public"."dumps" (
    "config_id" integer NOT NULL,
    "dump" text NOT NULL
) WITH (oids = false);


DROP TABLE IF EXISTS "files";
DROP SEQUENCE IF EXISTS files_id_seq;
CREATE SEQUENCE files_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 4306 CACHE 1;

CREATE TABLE "public"."files" (
    "id" integer DEFAULT nextval('files_id_seq') NOT NULL,
    "config_id" integer NOT NULL,
    "path" text NOT NULL,
    "content" bytea,
    CONSTRAINT "files_pkey" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "selected_config";
DROP SEQUENCE IF EXISTS selected_config_id_seq;
CREATE SEQUENCE selected_config_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 5 CACHE 1;

CREATE TABLE "public"."selected_config" (
    "id" integer DEFAULT nextval('selected_config_id_seq') NOT NULL,
    "config_id" integer,
    CONSTRAINT "selected_config_pkey" PRIMARY KEY ("id")
) WITH (oids = false);


ALTER TABLE ONLY "public"."analysis_tasks" ADD CONSTRAINT "parsing_tasks_config_id_fkey" FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dumps" ADD CONSTRAINT "dumps_config_id_fkey" FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."files" ADD CONSTRAINT "files_config_id_fkey" FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."selected_config" ADD CONSTRAINT "selected_config_config_id_fkey" FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE SET NULL NOT DEFERRABLE;

-- 2025-06-27 18:55:47.483276+00
