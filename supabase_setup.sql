-- Create transcriptions table
CREATE TABLE IF NOT EXISTS public.transcriptions (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    progress FLOAT NOT NULL,
    chunks JSONB,
    full_transcription TEXT,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create summaries table
CREATE TABLE IF NOT EXISTS public.summaries (
    id UUID PRIMARY KEY,
    transcribe_id UUID NOT NULL REFERENCES public.transcriptions(id),
    status TEXT NOT NULL,
    progress FLOAT NOT NULL,
    summary TEXT,
    error TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create a function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update the updated_at column
CREATE TRIGGER update_transcriptions_updated_at
BEFORE UPDATE ON public.transcriptions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_summaries_updated_at
BEFORE UPDATE ON public.summaries
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create storage bucket for audio files
-- Note: This needs to be done via the Supabase dashboard or API
-- as SQL doesn't directly manage storage buckets
