from django.http import HttpRequest

from core.rpc import Procedures
from modules.risk import service
from modules.risk.dto import RulesOutput

procedures = Procedures("risk")


@procedures.public("rules", output=RulesOutput, summary="The risk table and load rules the planner applies")
def rules(request: HttpRequest) -> RulesOutput:
    return service.rules()
