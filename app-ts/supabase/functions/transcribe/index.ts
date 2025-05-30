
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'jsr:@supabase/supabase-js@2'

interface TranscribeRequest {
  file_url: string
  file_name: string
  user_id?: string
}

interface TranscribeResponse {
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
      const { file_url, file_name, user_id }: TranscribeRequest = await req.json()
      
      // Generate unique transcription ID
      const transcriptionId = crypto.randomUUID()
      
      // Create transcription job in database
      const { error: insertError } = await supabase
        .from('transcriptions')
        .insert({
          id: transcriptionId,
          user_id: user_id,
          file_url: file_url,
          file_name: file_name,
          status: 'pending',
          progress: 0,
          created_at: new Date().toISOString()
        })

      if (insertError) {
        throw new Error(`Failed to create transcription job: ${insertError.message}`)
      }

      // Start background processing (non-blocking)
      EdgeRuntime.waitUntil(processTranscription(transcriptionId, file_url))

      return new Response(
        JSON.stringify({
          id: transcriptionId,
          status: 'pending',
          progress: 0
        } as TranscribeResponse),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    if (req.method === 'GET') {
      // Get transcription status
      const url = new URL(req.url)
      const pathSegments = url.pathname.split('/')
      const transcriptionId = pathSegments[pathSegments.length - 1]

      const { data, error } = await supabase
        .from('transcriptions')
        .select('*')
        .eq('id', transcriptionId)
        .single()

      if (error || !data) {
        return new Response(
          JSON.stringify({ error: 'Transcription not found' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      return new Response(
        JSON.stringify({
          id: data.id,
          status: data.status,
          progress: data.progress,
          transcription: data.full_transcription,
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

async function processTranscription(transcriptionId: string, fileUrl: string) {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
  )

  try {
    // Update status to processing
    await supabase
      .from('transcriptions')
      .update({ status: 'processing', progress: 0.1 })
      .eq('id', transcriptionId)

    // Download audio file
    console.log(`Downloading audio file: ${fileUrl}`)
    const audioResponse = await fetch(fileUrl)
    if (!audioResponse.ok) {
      throw new Error(`Failed to download audio file: ${audioResponse.statusText}`)
    }

    const audioBuffer = await audioResponse.arrayBuffer()
    const audioFile = new File([audioBuffer], 'audio.mp3', { type: 'audio/mpeg' })

    // Update progress
    await supabase
      .from('transcriptions')
      .update({ progress: 0.3 })
      .eq('id', transcriptionId)

    // Call OpenAI Whisper API
    const formData = new FormData()
    formData.append('file', audioFile)
    formData.append('model', 'whisper-1')

    const openaiResponse = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
      },
      body: formData,
    })

    if (!openaiResponse.ok) {
      throw new Error(`OpenAI API error: ${openaiResponse.statusText}`)
    }

    const transcriptionResult = await openaiResponse.json()

    // Update with completed transcription
    await supabase
      .from('transcriptions')
      .update({
        status: 'completed',
        progress: 1.0,
        full_transcription: transcriptionResult.text
      })
      .eq('id', transcriptionId)

    console.log(`Transcription completed for ${transcriptionId}`)

  } catch (error) {
    console.error(`Transcription failed for ${transcriptionId}:`, error)
    
    // Update status to failed
    await supabase
      .from('transcriptions')
      .update({
        status: 'failed',
        progress: 0,
        error: error.message
      })
      .eq('id', transcriptionId)
  }
}
