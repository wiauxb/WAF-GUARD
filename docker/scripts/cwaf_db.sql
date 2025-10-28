-- Adminer 4.17.1 PostgreSQL 17.4 (Debian 17.4-1.pgdg120+2) dump

DROP TABLE IF EXISTS "macrocall";
DROP SEQUENCE IF EXISTS macrocall_id_seq;
CREATE SEQUENCE macrocall_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 556961 CACHE 1;

CREATE TABLE "public"."macrocall" (
    "id" integer DEFAULT nextval('macrocall_id_seq') NOT NULL,
    "nodeid" integer NOT NULL,
    "macro_name" text,
    "ruleid" integer,
    CONSTRAINT "macrocall_pkey" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "macrodef";
CREATE TABLE "public"."macrodef" (
    "name" text NOT NULL,
    "ruleid" integer,
    CONSTRAINT "macrodef_pkey" PRIMARY KEY ("name")
) WITH (oids = false);


DROP TABLE IF EXISTS "symboltable";
DROP SEQUENCE IF EXISTS symboltable_id_seq;
CREATE SEQUENCE symboltable_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 650279 CACHE 1;

CREATE TABLE "public"."symboltable" (
    "id" integer DEFAULT nextval('symboltable_id_seq') NOT NULL,
    "file_path" text NOT NULL,
    "line_number" integer NOT NULL,
    "node_id" integer,
    CONSTRAINT "symboltable_pkey" PRIMARY KEY ("id")
) WITH (oids = false);


ALTER TABLE ONLY "public"."macrocall" ADD CONSTRAINT "macrocall_macro_name_fkey" FOREIGN KEY (macro_name) REFERENCES macrodef(name) NOT DEFERRABLE;
ALTER TABLE ONLY "public"."macrocall" ADD CONSTRAINT "macrocall_ruleid_fkey" FOREIGN KEY (ruleid) REFERENCES symboltable(id) NOT DEFERRABLE;

ALTER TABLE ONLY "public"."macrodef" ADD CONSTRAINT "macrodef_ruleid_fkey" FOREIGN KEY (ruleid) REFERENCES symboltable(id) NOT DEFERRABLE;

-- 2025-06-13 20:20:11.960444+00
