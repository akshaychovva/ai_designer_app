def generate_terraform(infra_state: dict) -> str:
    tf_code = []
    
    # VPC Generation
    if "vpc" in infra_state:
        vpc_cidr = infra_state["vpc"].get("cidr", "10.0.0.0/16")
        tf_code.append(f'resource "aws_vpc" "main" {{\n  cidr_block = "{vpc_cidr}"\n}}')
        
        # Subnets Generation
        subnets = infra_state["vpc"].get("subnets", [])
        for i, subnet in enumerate(subnets):
            subnet_type = subnet.get("type", "public")
            # Just a pseudo-cidr for representation
            subnet_cidr = f"10.0.{i+1}.0/24"
            tf_code.append(f'\nresource "aws_subnet" "subnet_{i+1}_{subnet_type}" {{\n  vpc_id     = aws_vpc.main.id\n  cidr_block = "{subnet_cidr}"\n}}')

    return "\n".join(tf_code)
