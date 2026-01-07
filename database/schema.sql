-- FinTrackable Database Schema
-- Updated: 2026-01-06

-- DISABLE RLS FOR ALL TABLES (As requested)
ALTER TABLE public.user DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences DISABLE ROW LEVEL SECURITY;

-- Table: public.user
CREATE TABLE public.user (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  email text,
  first_name text,
  second_name text,
  password text NOT NULL,
  CONSTRAINT user_pkey PRIMARY KEY (id)
);

-- Table: public.categories
CREATE TABLE public.categories (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  name text NOT NULL,
  rules jsonb DEFAULT '[]'::jsonb,
  color text DEFAULT '#9ca3af'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  percentage bigint,
  CONSTRAINT categories_pkey PRIMARY KEY (id),
  CONSTRAINT categories_user_id_fkey1 FOREIGN KEY (user_id) REFERENCES public.user(id)
);

-- Table: public.transactions
CREATE TABLE public.transactions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  datum date NOT NULL,
  bedrag numeric NOT NULL,
  naam_tegenpartij text,
  omschrijving text,
  rekeningnummer text,
  categorie_id uuid,
  hash text NOT NULL UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  is_confirmed boolean DEFAULT false,
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user(id),
  CONSTRAINT transactions_categorie_id_fkey FOREIGN KEY (categorie_id) REFERENCES public.categories(id)
);

-- Table: public.user_preferences
CREATE TABLE public.user_preferences (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE,
  investment_goal_percentage numeric DEFAULT 20.00,
  default_categories jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_preferences_pkey PRIMARY KEY (id),
  CONSTRAINT user_preferences_user_id_fkey1 FOREIGN KEY (user_id) REFERENCES public.user(id)
);
