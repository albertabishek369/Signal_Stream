-- signalstream/supabase_schema.sql - FINAL & COMPLETE VERSION

-- Step 1: Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Step 2: Create the Profiles table to store all public user data.
-- This table is linked 1-to-1 with Supabase's private auth.users table.
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email VARCHAR(255),
  country TEXT,
  phone TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Set permissions for the profiles table
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own profile." ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can insert their own profile." ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update their own profile." ON public.profiles FOR UPDATE USING (auth.uid() = id);


-- Step 4: Create the Subscriptions table
-- It now correctly references the new profiles table.
CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    plan_type TEXT NOT NULL, -- e.g., 'free', 'founder', 'scale'
    status TEXT NOT NULL,
    razorpay_subscription_id TEXT UNIQUE,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Set permissions for the subscriptions table
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own subscription." ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);


-- Step 5: Create the Products table
CREATE TABLE public.products (
    product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    product_description TEXT NOT NULL,
    target_audience TEXT,
    pain_points_solved TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Set permissions for the products table
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own products." ON public.products FOR ALL USING (auth.uid() = user_id);


-- Step 6: Create the Streams table
CREATE TABLE public.streams (
    stream_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_id UUID REFERENCES public.products(product_id) ON DELETE CASCADE,
    stream_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    target TEXT NOT NULL,
    ai_strictness TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    execution_frequency_minutes INTEGER NOT NULL,
    last_executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Set permissions for the streams table
ALTER TABLE public.streams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own streams." ON public.streams FOR ALL USING (auth.uid() = user_id);


-- Step 7: Create the Leads table
CREATE TABLE public.leads (
    lead_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    stream_id UUID REFERENCES public.streams(stream_id) ON DELETE CASCADE,
    source_platform TEXT NOT NULL,
    author_username TEXT NOT NULL,
    content_text TEXT NOT NULL,
    content_url TEXT,
    ai_reasoning TEXT,
    ai_pain_point TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add a unique constraint to prevent duplicate leads for the same user
ALTER TABLE public.leads ADD CONSTRAINT unique_lead_url_for_user UNIQUE (user_id, content_url);

-- Set permissions for the leads table
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own leads." ON public.leads FOR ALL USING (auth.uid() = user_id);


-- Step 8: Create the Plan Limits helper table
CREATE TABLE public.plan_limits (
    plan_type TEXT PRIMARY KEY,
    max_streams INTEGER NOT NULL,
    daily_analyses INTEGER NOT NULL
);

-- Allow all users to read the plan limits
ALTER TABLE public.plan_limits ENABLE ROW LEVEL SECURITY;
CREATE POLICY "All users can view plan limits." ON public.plan_limits FOR SELECT USING (true);

-- Step 9: Insert the plan limits data
INSERT INTO public.plan_limits (plan_type, max_streams, daily_analyses) VALUES
('free', 1, 50),
('founder', 5, 1000),
('scale', -1, 10000); -- -1 for unlimited
