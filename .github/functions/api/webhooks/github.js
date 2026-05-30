/**
 * AladdinAI GitHub Bot Webhook Handler
 * Cloudflare Pages Function for handling GitHub App events
 *
 * Supports:
 * - Pull Request events (opened, synchronize, closed)
 * - Issue events (opened, closed, labeled)
 * - Issue comment events
 * - Pull Request review events
 */

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-GitHub-Event, X-Hub-Signature-256',
  'Content-Type': 'application/json'
};

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders
  });
}

export async function onRequestPost(context) {
  try {
    const { request, env } = context;

    // Verify GitHub webhook signature
    const signature = request.headers.get('X-Hub-Signature-256');
    const event = request.headers.get('X-GitHub-Event');

    if (!signature || !event) {
      return new Response(
        JSON.stringify({ error: 'Missing GitHub headers' }),
        { status: 400, headers: corsHeaders }
      );
    }

    // Read webhook secret from environment
    const webhookSecret = env.WEBHOOK_SECRET || env.GITHUB_WEBHOOK_SECRET;
    if (!webhookSecret) {
      console.error('WEBHOOK_SECRET not configured');
      return new Response(
        JSON.stringify({ error: 'Webhook secret not configured' }),
        { status: 500, headers: corsHeaders }
      );
    }

    // Read raw body BEFORE parsing (GitHub signs the raw bytes)
    const rawBody = await request.text();

    // Verify signature against raw body
    const isValid = await verifySignature(
      rawBody,
      signature,
      webhookSecret
    );

    if (!isValid) {
      return new Response(
        JSON.stringify({ error: 'Invalid signature' }),
        { status: 401, headers: corsHeaders }
      );
    }

    // Now parse JSON from raw body
    let payload;
    try {
      payload = JSON.parse(rawBody);
    } catch (e) {
      return new Response(
        JSON.stringify({ error: 'Invalid JSON payload' }),
        { status: 400, headers: corsHeaders }
      );
    }

    // Route to appropriate handler
    let response;
    switch (event) {
      case 'pull_request':
        response = await handlePullRequest(payload, env);
        break;
      case 'issues':
        response = await handleIssue(payload, env);
        break;
      case 'issue_comment':
        response = await handleIssueComment(payload, env);
        break;
      case 'pull_request_review':
        response = await handlePullRequestReview(payload, env);
        break;
      case 'ping':
        response = { message: 'pong', event };
        break;
      default:
        response = { message: 'Event received but not handled', event };
    }

    return new Response(
      JSON.stringify(response),
      { status: 200, headers: corsHeaders }
    );

  } catch (error) {
    console.error('GitHub Webhook Error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: corsHeaders }
    );
  }
}

async function verifySignature(payload, signature, secret) {
  try {
    const encoder = new TextEncoder();

    // Import secret as HMAC key
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );

    // Compute HMAC-SHA256 signature
    const signatureBytes = await crypto.subtle.sign(
      'HMAC',
      key,
      encoder.encode(payload)
    );

    // Convert to hex string with 'sha256=' prefix (GitHub format)
    const expectedSignature = 'sha256=' + Array.from(new Uint8Array(signatureBytes))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');

    // Constant-time comparison to prevent timing attacks
    if (signature.length !== expectedSignature.length) {
      return false;
    }

    let result = 0;
    for (let i = 0; i < signature.length; i++) {
      result |= signature.charCodeAt(i) ^ expectedSignature.charCodeAt(i);
    }

    return result === 0;
  } catch (error) {
    console.error('Signature verification error:', error);
    return false;
  }
}

async function handlePullRequest(payload, env) {
  const { action, pull_request, repository } = payload;

  if (!['opened', 'synchronize', 'closed'].includes(action)) {
    return { message: 'PR action not handled', action };
  }

  const comment = generatePRComment(action, pull_request);

  if (comment) {
    await postComment(
      repository.full_name,
      pull_request.number,
      comment,
      env
    );
  }

  return { message: 'PR handled', action, pr: pull_request.number };
}

async function handleIssue(payload, env) {
  const { action, issue, repository } = payload;

  if (!['opened', 'closed', 'labeled'].includes(action)) {
    return { message: 'Issue action not handled', action };
  }

  const comment = generateIssueComment(action, issue);

  if (comment) {
    await postComment(
      repository.full_name,
      issue.number,
      comment,
      env
    );
  }

  return { message: 'Issue handled', action, issue: issue.number };
}

async function handleIssueComment(payload, env) {
  const { action, comment, issue, repository } = payload;

  if (action !== 'created') {
    return { message: 'Comment action not handled', action };
  }

  // Check if bot is mentioned
  if (comment.body.includes('@AladdinAI')) {
    const reply = generateMentionReply(comment, issue);

    await postComment(
      repository.full_name,
      issue.number,
      reply,
      env
    );
  }

  return { message: 'Comment handled', action };
}

async function handlePullRequestReview(payload, env) {
  const { action, review, pull_request, repository } = payload;

  if (action !== 'submitted') {
    return { message: 'Review action not handled', action };
  }

  // React to reviews if needed
  return { message: 'Review handled', action, pr: pull_request.number };
}

function generatePRComment(action, pr) {
  const author = pr.user.login;

  switch (action) {
    case 'opened':
      return `👋 Hey @${author}! Thanks for the PR. I'll keep an eye on this one.\n\n` +
             `**Quick stats:**\n` +
             `- Files changed: ${pr.changed_files}\n` +
             `- Additions: +${pr.additions}\n` +
             `- Deletions: -${pr.deletions}`;

    case 'closed':
      if (pr.merged) {
        return `🎉 Merged! Nice work @${author}. This one's going into the history books.`;
      }
      return `PR closed without merge. No worries @${author}, happens to the best of us.`;

    default:
      return null;
  }
}

function generateIssueComment(action, issue) {
  const author = issue.user.login;

  switch (action) {
    case 'opened':
      return `👀 New issue spotted. Thanks for reporting @${author}!\n\n` +
             `I'll track this one. Feel free to add more details if needed.`;

    case 'closed':
      return `✅ Issue closed. Good riddance! Thanks @${author}.`;

    default:
      return null;
  }
}

function generateMentionReply(comment, issue) {
  const author = comment.user.login;

  return `Hey @${author}! You called?\n\n` +
         `I'm here and watching. What do you need help with?`;
}

async function postComment(repoFullName, issueNumber, body, env) {
  const githubToken = env.GITHUB_TOKEN || env.PATH_TOKEN || env.GITHUB_APP_TOKEN;

  if (!githubToken) {
    console.error('GitHub token not configured');
    return { success: false, error: 'Token not configured' };
  }

  const url = `https://api.github.com/repos/${repoFullName}/issues/${issueNumber}/comments`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${githubToken}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'AladdinAI-Bot'
      },
      body: JSON.stringify({ body })
    });

    // Handle rate limiting
    if (response.status === 403) {
      const rateLimitRemaining = response.headers.get('X-RateLimit-Remaining');
      const rateLimitReset = response.headers.get('X-RateLimit-Reset');

      if (rateLimitRemaining === '0') {
        const resetTime = new Date(parseInt(rateLimitReset) * 1000);
        console.error(`Rate limit exceeded. Resets at ${resetTime.toISOString()}`);
        return { success: false, error: 'Rate limit exceeded' };
      }
    }

    // Handle authentication errors
    if (response.status === 401) {
      console.error('GitHub API authentication failed - token may be invalid or expired');
      return { success: false, error: 'Authentication failed' };
    }

    // Handle permission errors
    if (response.status === 403) {
      console.error('GitHub API permission denied - token may lack required scopes');
      return { success: false, error: 'Permission denied' };
    }

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`GitHub API error (${response.status}):`, errorBody);
      return {
        success: false,
        error: `GitHub API error: ${response.status}`,
        details: errorBody
      };
    }

    const result = await response.json();
    return { success: true, data: result };

  } catch (error) {
    console.error('Failed to post comment:', error.message);
    return {
      success: false,
      error: 'Network or fetch error',
      details: error.message
    };
  }
}
