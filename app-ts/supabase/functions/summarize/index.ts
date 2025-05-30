
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'jsr:@supabase/supabase-js@2'

interface SummarizeRequest {
  transcribe_id: string
  user_id?: string
}

interface SummarizeResponse {
  id: string
  status: string
  progress: number
}

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    if (req.method === 'POST') {
      const { transcribe_id, user_id }: SummarizeRequest = await req.json()
      
      // Validate transcription exists and is completed
      const { data: transcription, error: transcriptionError } = await supabase
        .from('transcriptions')
        .select('*')
        .eq('id', transcribe_id)
        .single()

      if (transcriptionError || !transcription) {
        return new Response(
          JSON.stringify({ error: 'Transcription not found' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      if (transcription.status !== 'completed') {
        return new Response(
          JSON.stringify({ error: `Transcription not completed (status: ${transcription.status})` }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      // Generate unique summary ID
      const summaryId = crypto.randomUUID()
      
      // Create summary job in database
      const { error: insertError } = await supabase
        .from('summaries')
        .insert({
          id: summaryId,
          transcribe_id: transcribe_id,
          user_id: user_id,
          status: 'pending',
          progress: 0,
          created_at: new Date().toISOString()
        })

      if (insertError) {
        throw new Error(`Failed to create summary job: ${insertError.message}`)
      }

      // Start background processing (non-blocking)
      EdgeRuntime.waitUntil(processSummarization(summaryId, transcription.full_transcription))

      return new Response(
        JSON.stringify({
          id: summaryId,
          status: 'pending',
          progress: 0
        } as SummarizeResponse),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    if (req.method === 'GET') {
      // Get summary status
      const url = new URL(req.url)
      const pathSegments = url.pathname.split('/')
      const summaryId = pathSegments[pathSegments.length - 1]

      const { data, error } = await supabase
        .from('summaries')
        .select('*')
        .eq('id', summaryId)
        .single()

      if (error || !data) {
        return new Response(
          JSON.stringify({ error: 'Summary not found' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      return new Response(
        JSON.stringify({
          id: data.id,
          status: data.status,
          progress: data.progress,
          summary: data.summary,
          error: data.error
        }),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function processSummarization(summaryId: string, transcriptionText: string) {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
  )

  try {
    // Update status to processing
    await supabase
      .from('summaries')
      .update({ status: 'processing', progress: 0.1 })
      .eq('id', summaryId)

    // Split text into chunks if too large
    const maxChunkSize = 8000 // Conservative chunk size for GPT-4
    const chunks = splitTextIntoChunks(transcriptionText, maxChunkSize)
    
    // Process chunks and create summaries
    const chunkSummaries = []
    for (let i = 0; i < chunks.length; i++) {
      const chunkSummary = await summarizeChunk(chunks[i])
      chunkSummaries.push(chunkSummary)
      
      // Update progress
      const progress = 0.1 + (0.6 * (i + 1) / chunks.length)
      await supabase
        .from('summaries')
        .update({ progress })
        .eq('id', summaryId)
    }

    // Create final comprehensive summary
    const combinedSummaries = chunkSummaries.join('\n\n')
    const finalSummary = await createFinalSummary(combinedSummaries)

    // Update with completed summary
    await supabase
      .from('summaries')
      .update({
        status: 'completed',
        progress: 1.0,
        summary: finalSummary
      })
      .eq('id', summaryId)

    console.log(`Summarization completed for ${summaryId}`)

  } catch (error) {
    console.error(`Summarization failed for ${summaryId}:`, error)
    
    // Update status to failed
    await supabase
      .from('summaries')
      .update({
        status: 'failed',
        progress: 0,
        error: error.message
      })
      .eq('id', summaryId)
  }
}

function splitTextIntoChunks(text: string, maxChunkSize: number): string[] {
  const chunks = []
  const sentences = text.split(/[.!?]+/)
  let currentChunk = ''

  for (const sentence of sentences) {
    if ((currentChunk + sentence).length > maxChunkSize && currentChunk) {
      chunks.push(currentChunk.trim())
      currentChunk = sentence
    } else {
      currentChunk += sentence + '. '
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim())
  }

  return chunks
}

async function summarizeChunk(chunk: string): Promise<string> {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant that summarizes text accurately and concisely.'
        },
        {
          role: 'user',
          content: `Please summarize the following text, preserving key information, quotes, and details:\n\n${chunk}`
        }
      ],
      max_tokens: 1500,
      temperature: 0.3
    })
  })

  if (!response.ok) {
    throw new Error(`OpenAI API error: ${response.statusText}`)
  }

  const result = await response.json()
  return result.choices[0].message.content
}

async function createFinalSummary(combinedSummaries: string): Promise<string> {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: `You are a helpful assistant that creates well-structured, comprehensive summaries.
Your task is to create a final summary from the provided text, which consists of summaries of different parts of a transcription.
IMPORTANT: Auto-correct any misspelled words and names. Mention corrections like "John (Auto-corrected)", "New York (Auto-corrected)" etc.
Format the summary in markdown with clear sections.
At the end, extract and list metadata like dates, URLs, people, organizations, and key topics mentioned.`
        },
        {
          role: 'user',
          content: `Here are the summaries to combine into a final comprehensive summary:\n\n${combinedSummaries}`
        }
      ],
      max_tokens: 2000,
      temperature: 0.3
    })
  })

  if (!response.ok) {
    throw new Error(`OpenAI API error: ${response.statusText}`)
  }

  const result = await response.json()
  return result.choices[0].message.content
}
