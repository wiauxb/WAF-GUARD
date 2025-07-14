-- Adminer 5.3.0 PostgreSQL 17.5 dump

\connect "chatbot";

DROP TABLE IF EXISTS "checkpoint_blobs";
CREATE TABLE "public"."checkpoint_blobs" (
    "thread_id" text NOT NULL,
    "checkpoint_ns" text DEFAULT '' NOT NULL,
    "channel" text NOT NULL,
    "version" text NOT NULL,
    "type" text NOT NULL,
    "blob" bytea,
    CONSTRAINT "checkpoint_blobs_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "channel", "version")
)
WITH (oids = false);

CREATE INDEX checkpoint_blobs_thread_id_idx ON public.checkpoint_blobs USING btree (thread_id);


DROP TABLE IF EXISTS "checkpoint_migrations";
CREATE TABLE "public"."checkpoint_migrations" (
    "v" integer NOT NULL,
    CONSTRAINT "checkpoint_migrations_pkey" PRIMARY KEY ("v")
)
WITH (oids = false);


DROP TABLE IF EXISTS "checkpoint_writes";
CREATE TABLE "public"."checkpoint_writes" (
    "thread_id" text NOT NULL,
    "checkpoint_ns" text DEFAULT '' NOT NULL,
    "checkpoint_id" text NOT NULL,
    "task_id" text NOT NULL,
    "idx" integer NOT NULL,
    "channel" text NOT NULL,
    "type" text,
    "blob" bytea NOT NULL,
    "task_path" text DEFAULT '' NOT NULL,
    CONSTRAINT "checkpoint_writes_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx")
)
WITH (oids = false);

CREATE INDEX checkpoint_writes_thread_id_idx ON public.checkpoint_writes USING btree (thread_id);


DROP TABLE IF EXISTS "checkpoints";
CREATE TABLE "public"."checkpoints" (
    "thread_id" text NOT NULL,
    "checkpoint_ns" text DEFAULT '' NOT NULL,
    "checkpoint_id" text NOT NULL,
    "parent_checkpoint_id" text,
    "type" text,
    "checkpoint" jsonb NOT NULL,
    "metadata" jsonb DEFAULT '{}' NOT NULL,
    CONSTRAINT "checkpoints_pkey" PRIMARY KEY ("thread_id", "checkpoint_ns", "checkpoint_id")
)
WITH (oids = false);

CREATE INDEX checkpoints_thread_id_idx ON public.checkpoints USING btree (thread_id);


DROP TABLE IF EXISTS "users";
DROP SEQUENCE IF EXISTS users_users_id_seq;
CREATE SEQUENCE users_users_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 3 CACHE 1;

CREATE TABLE "public"."users" (
    "users_id" text DEFAULT nextval('users_users_id_seq')::text NOT NULL,
    "username" text NOT NULL,
    "password" text NOT NULL,
    CONSTRAINT "users_pkey" PRIMARY KEY ("users_id")
)
WITH (oids = false);

CREATE UNIQUE INDEX users_username ON public.users USING btree (username);


DROP TABLE IF EXISTS "users_threads";
DROP SEQUENCE IF EXISTS users_threads_thread_id_seq;
CREATE SEQUENCE users_threads_thread_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 START 3 CACHE 1;

CREATE TABLE "public"."users_threads" (
    "thread_id" text DEFAULT nextval('users_threads_thread_id_seq')::text NOT NULL,
    "user_id" text NOT NULL,
    "title" text DEFAULT 'New Thread' NOT NULL,

    "created_at" TIMESTAMPTZ DEFAULT now() NOT NULL,
    "updated_at" TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT "users_threads_pkey" PRIMARY KEY ("thread_id")
)
WITH (oids = false);


ALTER TABLE ONLY "public"."checkpoint_blobs" ADD CONSTRAINT "checkpoint_blobs_thread_id_fkey" FOREIGN KEY (thread_id) REFERENCES users_threads(thread_id) ON UPDATE CASCADE ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."checkpoint_writes" ADD CONSTRAINT "checkpoint_writes_thread_id_fkey" FOREIGN KEY (thread_id) REFERENCES users_threads(thread_id) ON UPDATE CASCADE ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."checkpoints" ADD CONSTRAINT "checkpoints_thread_id_fkey" FOREIGN KEY (thread_id) REFERENCES users_threads(thread_id) ON UPDATE CASCADE ON DELETE CASCADE NOT DEFERRABLE;

ALTER TABLE ONLY "public"."users_threads" ADD CONSTRAINT "users_threads_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(users_id) ON UPDATE CASCADE ON DELETE CASCADE NOT DEFERRABLE;

-- 2025-07-07 14:51:47 UTC
