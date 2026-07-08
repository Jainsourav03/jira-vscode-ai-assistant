
export type TicketComment = {
    author?: string;
    body: string;
};

export type Ticket = {
    key: string;
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    url?: string;
    assigneeEmail?: string;
    projectKey?: string;
    receivedAt?: string;
    assigneeDisplayName?: string;  
    comments?: Array<{
        author?: string;
        body: string;
    }>;
};

export type TicketAssignedEvent = {
    event_type: 'ticket_assigned';
    ticket_key: string;
    ticket_title: string;
    ticket_description?: string;
    ticket_status?: string;
    ticket_priority?: string;
    ticket_url?: string;
    assignee_email?: string;
    comments?: string[];
};

export type TicketMetadata = {
    projectKey?: string;
    assigneeDisplayName?: string;
};

export type DeveloperContextSubmission = {
    userEmail: string;
    additionalContext: string;
    repoPath?: string;
    branchName?: string;
    notes?: string;
};
export type SubmitContextMessage = {
    type: 'submitContext';
    ticketKey: string;
    additionalContext: string;
};
export type WebviewReadyMessage = {
    type: 'webviewReady';
};
export type ConnectionStatus =
    | 'connected'
    | 'connecting'
    | 'disconnected'
    | 'error';