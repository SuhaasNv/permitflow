/**
 * Policy pages (US-057). Plain statements of what the service actually does, written for Singapore's
 * Personal Data Protection Act 2012 and reviewed against the code, not a template. Every claim here has a
 * counterpart in docs/11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md. Dates are the last review, not the deploy.
 */

export type PolicySlug = 'privacy' | 'terms' | 'cookies'

export interface PolicySection {
  heading: string
  paragraphs: string[]
  bullets?: string[]
}

export interface Policy {
  slug: PolicySlug
  title: string
  summary: string
  reviewed: string
  sections: PolicySection[]
}

export const OPERATOR_NAME = 'Suhaas Nv'
export const OPERATOR_URL = 'https://github.com/SuhaasNv/permitflow'
const REVIEWED = '19 September 2026'

export const POLICIES: Record<PolicySlug, Policy> = {
  privacy: {
    slug: 'privacy',
    title: 'Privacy policy',
    summary:
      'PermitFlow is a demonstration built for an engineering assessment. It is not a government service and it is not meant for real licence applications. This page says what the demonstration collects, where it goes and how long it stays.',
    reviewed: REVIEWED,
    sections: [
      {
        heading: 'Who operates this service',
        paragraphs: [
          `PermitFlow is operated by ${OPERATOR_NAME} as a portfolio and assessment project. The source code is public at ${OPERATOR_URL}. There is no company behind it and nothing is sold through it.`,
        ],
      },
      {
        heading: 'Do not use real personal data',
        paragraphs: [
          'The demonstration accounts are shared and their passwords are published. Anything you type or upload can be seen by anyone who signs in with the same demonstration account, and by the operator. Use the fictional demonstration documents provided in the repository. Do not upload real identity documents, real business records or anyone else’s personal data.',
        ],
      },
      {
        heading: 'What is collected',
        paragraphs: ['When you use the demonstration, the service stores:'],
        bullets: [
          'the account you sign in with (a seeded demonstration email address, a display name and a role);',
          'what you enter in the application form (business name, UEN, a contact name, email and phone, premises address, operating details, declarations);',
          'the files you upload (PDF, PNG, JPG or TXT, at most 10 MB each) and the text extracted from PDF and TXT files;',
          'the results of the automated document checks, including short quotes from the document as evidence;',
          'an audit trail of actions on each application (who did what and when), notifications, and server request logs with IP address, path, status and timing, which the hosting platform keeps for seven days.',
        ],
      },
      {
        heading: 'Why it is collected',
        paragraphs: [
          'Only to make the demonstration work: to save an application, to check uploaded documents against the form, to let a licensing officer review and respond, to issue a demonstration licence, and to keep a record of what happened. Nothing is used for marketing, profiling or advertising, and no data is sold or shared for any other purpose.',
        ],
      },
      {
        heading: 'Automated document checks and where data travels',
        paragraphs: [
          'Each uploaded document is checked automatically. When the live provider is switched on, the document type, the text extracted from the document (capped at 20,000 characters) and the matching section of the form are sent to OpenAI (United States) to produce a structured result. The check is advisory: it never decides an application; a person does.',
          'When tracing is switched on, a record of each check is also sent to LangSmith (LangChain, United States) so the operator can debug it. That record carries the result, the model used, timing and the identifiers of the application and document; the document text and the form data are withheld from it by default.',
          'The service itself runs on Railway in the United States (us-west2, California), with a PostgreSQL database and a file volume there. In the terms of the Personal Data Protection Act 2012 these are transfers out of Singapore, and they are made under the demonstration’s standard, not under a contract that would satisfy the Transfer Limitation Obligation for a production service.',
        ],
      },
      {
        heading: 'Cookies and storage in your browser',
        paragraphs: [
          'The service sets no cookies. It keeps your sign-in token in your browser’s session storage until you sign out or close the tab, and remembers whether you collapsed the side navigation in local storage. Neither is shared with anyone and neither is used for tracking. There are no analytics, no advertising scripts and no third-party embeds; fonts are served from this site.',
        ],
      },
      {
        heading: 'How long data is kept',
        paragraphs: [
          'Demonstration data is kept until the operator resets the environment, which happens without notice. There is no automatic deletion schedule yet: a production version would delete extracted document text ninety days after an application reaches its final state. Server request logs are kept by the hosting platform for seven days.',
        ],
      },
      {
        heading: 'Security',
        paragraphs: [
          'Passwords are hashed with Argon2; sessions use signed tokens that expire after eight hours; every request is authorised on the server; uploads are checked by type and size and served only through authorised endpoints; data moves over HTTPS. The full threat model and its known gaps are published in the repository.',
        ],
      },
      {
        heading: 'Your rights and how to reach the operator',
        paragraphs: [
          'You can ask for what the demonstration holds about you, ask for it to be corrected or deleted, or withdraw from the demonstration at any time by opening an issue at the repository linked above. Because the accounts are shared and the environment is reset regularly, the practical answer to most requests is a reset of the environment.',
        ],
      },
      {
        heading: 'Changes',
        paragraphs: ['This page is updated whenever the service changes what it collects or where it sends it. The date at the top is the last review.'],
      },
    ],
  },
  terms: {
    slug: 'terms',
    title: 'Terms of use',
    summary:
      'Short terms for a demonstration. They exist so that no one mistakes PermitFlow for a licensing authority or relies on it for anything real.',
    reviewed: REVIEWED,
    sections: [
      {
        heading: 'What PermitFlow is',
        paragraphs: [
          `PermitFlow is a fictional licensing workflow built by ${OPERATOR_NAME} for a software engineering assessment. The licence types, issuing bodies, registrars, certificates and documents in it are invented. It is not connected to any government agency and it does not grant, renew or record any real licence or permit.`,
        ],
      },
      {
        heading: 'Using the demonstration',
        paragraphs: ['By signing in you agree to:'],
        bullets: [
          'use only the demonstration accounts and the fictional documents provided, and not upload real personal data or documents belonging to other people;',
          'not attempt to bypass authorisation, probe other accounts, disrupt the service or extract data that is not yours to see;',
          'not present any output of the service, including a demonstration licence certificate, as a real document.',
        ],
      },
      {
        heading: 'Automated checks are advisory',
        paragraphs: [
          'Document checks are produced by an automated system and can be wrong. They never change the status of an application; a person reviews and decides. A demonstration officer’s decision is part of the demonstration and has no effect outside it.',
        ],
      },
      {
        heading: 'No warranty, no liability',
        paragraphs: [
          'The service is provided as is, for demonstration, without any warranty of availability, accuracy or fitness for a purpose. The environment may be reset, changed or withdrawn at any time without notice. To the extent permitted by law, the operator accepts no liability for any loss arising from use of the demonstration.',
        ],
      },
      {
        heading: 'Payments and refunds',
        paragraphs: ['Nothing is sold and nothing is charged, so there is no refund policy.'],
      },
      {
        heading: 'Intellectual property',
        paragraphs: [
          'The source code is public so that it can be reviewed; no open-source licence has been granted, so all rights are reserved apart from viewing it. The typefaces are used under the SIL Open Font License. The brand mark, page designs and fictional demonstration documents belong to the operator and are made available for review of the assessment only.',
        ],
      },
      {
        heading: 'Governing law',
        paragraphs: ['These terms are governed by the laws of Singapore.'],
      },
    ],
  },
  cookies: {
    slug: 'cookies',
    title: 'Cookie policy',
    summary: 'PermitFlow sets no cookies, so there is no banner to click and nothing to opt out of.',
    reviewed: REVIEWED,
    sections: [
      {
        heading: 'No cookies',
        paragraphs: [
          'The service does not set any cookie, first-party or third-party. It uses no analytics, no advertising technology and no embedded content from other sites.',
        ],
      },
      {
        heading: 'What the browser stores instead',
        paragraphs: ['Two items, both essential to the service working and neither used for tracking:'],
        bullets: [
          'your sign-in token, in session storage, removed when you sign out or close the tab;',
          'whether you collapsed the side navigation, in local storage.',
        ],
      },
      {
        heading: 'Why there is no consent banner',
        paragraphs: [
          'Singapore’s Personal Data Protection Act 2012 has no cookie-specific consent rule, and the European ePrivacy rules exempt storage that is strictly necessary to provide a service the visitor asked for. Nothing here goes beyond that, so a banner would ask consent for nothing.',
        ],
      },
    ],
  },
}
