import asyncio
import base64
import binascii
import json
import logging
import os
import sys
from urllib.parse import urlparse

from runners.agent_container import (  # noqa:E402
    arg_parser,
    create_agent_with_args,
    AriesAgent,
)


class AliceAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        aip: int = 20,
        endorser_role: str = None,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Alice",
            no_auto=no_auto,
            seed=None,
            aip=aip,
            endorser_role=endorser_role,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

async def input_invitation(agent_container, details):
    agent_container.agent._connection_ready = asyncio.Future()
    b64_invite = None
    try:
        details = urlparse(details)
        query = details.query
        if query and "c_i=" in query:
            pos = query.index("c_i=") + 4
            b64_invite = query[pos:]
        elif query and "oob=" in query:
            pos = query.index("oob=") + 4
            b64_invite = query[pos:]
        else:
            b64_invite = details
    except ValueError:
        b64_invite = details

    if b64_invite:
        try:
            padlen = 4 - len(b64_invite) % 4
            if padlen <= 2:
                b64_invite += "=" * padlen
            invite_json = base64.urlsafe_b64decode(b64_invite)
            details = invite_json.decode("utf-8")
        except binascii.Error:
            pass
        except UnicodeDecodeError:
            pass

    if details:
        try:
            details = json.loads(details)
            await agent_container.input_invitation(details, wait=True)
        except json.JSONDecodeError as e:
            print("Invalid invitation:", str(e))

async def main(args):
    alice_agent = await create_agent_with_args(args, ident="alice")

    print(
        "#7 Provision an agent and wallet, get back configuration details"
        + (
            f" (Wallet type: {alice_agent.wallet_type})"
            if alice_agent.wallet_type
            else ""
        )
    )
    agent = AliceAgent(
        "alice.agent",
        alice_agent.start_port,
        alice_agent.start_port + 1,
        genesis_data=alice_agent.genesis_txns,
        genesis_txn_list=alice_agent.genesis_txn_list,
        no_auto=alice_agent.no_auto,
        tails_server_base_url=alice_agent.tails_server_base_url,
        revocation=alice_agent.revocation,
        timing=alice_agent.show_timing,
        multitenant=alice_agent.multitenant,
        mediation=alice_agent.mediation,
        wallet_type=alice_agent.wallet_type,
        aip=alice_agent.aip,
        endorser_role=alice_agent.endorser_role,
    )

    await alice_agent.initialize(the_agent=agent)

    while True:
        url = input("Input invitation URL: ")
        await input_invitation(alice_agent, url)


    

if __name__ == "__main__":
    parser = arg_parser(ident="alice", port=8030)
    args = parser.parse_args()
    
    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)